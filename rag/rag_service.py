"""
总结服务类：将用户提问和参考资料给模型进行总结回复
"""
import re
import os
import threading

import bm25s
import jieba
from langchain_core.documents import Document

from rag.vector_store import VectorStoreService
from utils.config_handler import chroma_conf
from utils.prompt_loader import load_rag_prompts
from utils.logger_handler import logger
from langchain_core.prompts import PromptTemplate
from model.factory import get_chat_model
from langchain_core.output_parsers import StrOutputParser

class RagSummarizeService(object):
    """RAG 服务入口，负责检索、重排、总结和来源整理。"""

    def __init__(self):
        """初始化向量库、提示词链路和检索相关参数。"""
        self.vector_store = VectorStoreService()
        self._collection_ready_checked = False
        self._repair_lock = threading.Lock()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = get_chat_model()
        self.chain = self._init_chain()
        self.top_k = chroma_conf["k"]
        self.candidate_k = chroma_conf.get("candidate_k", max(self.top_k * 2, self.top_k))
        self.min_relevance_score = chroma_conf.get("min_relevance_score", 0.0)
        self.rrf_k = chroma_conf.get("rrf_k", 60)
        self.bm25_k1 = chroma_conf.get("bm25_k1", 1.5)
        self.bm25_b = chroma_conf.get("bm25_b", 0.75)
        self.cross_encoder_enabled = (
            chroma_conf.get("cross_encoder_rerank_enabled", False)
            or os.getenv("ENABLE_CROSS_ENCODER_RERANK", "").lower() in {"1", "true", "yes", "on"}
        )
        self.cross_encoder_model_name = chroma_conf.get("cross_encoder_model_name", "BAAI/bge-reranker-base")
        self.cross_encoder_top_n = chroma_conf.get("cross_encoder_top_n", max(self.top_k * 2, self.top_k))
        self._bm25_lock = threading.Lock()
        self._bm25_cache = None
        self._cross_encoder_lock = threading.Lock()
        self._cross_encoder_model = None
        self._cross_encoder_unavailable = False
        self.synonym_map = {
            "边缘行者": ["赛博朋克边缘行者", "cyberpunk edgerunners", "赛博浪客"],
            "赛博浪客": ["赛博朋克边缘行者", "cyberpunk edgerunners"],
            "大卫": ["大卫马丁内斯", "david martinez"],
            "露西": ["lucy", "lucyna kushinada"],
            "丽贝卡": ["rebecca"],
            "瑞贝卡": ["丽贝卡", "rebecca"],
            "曼恩": ["maine", "团队领袖", "赛博精神病", "大卫引路人"],
            "琦薇": ["kiwi", "黑客", "网络黑客", "团队成员"],
            "琪薇": ["琦薇", "kiwi", "黑客"],
            "斯安威斯坦": ["sandevistan", "沙德维斯坦", "军用脊椎"],
            "沙德维斯坦": ["sandevistan", "斯安威斯坦", "军用脊椎"],
            "赛博精神病": ["cyberpsychosis", "义体负荷", "精神崩溃"],
            "荒坂": ["arasaka", "公司", "公司势力"],
            "夜之城": ["night city", "城市", "阶层", "公司压迫"],
            "relic": ["relic芯片", "强尼银手", "v"],
            "soulkiller": ["灵魂杀手", "荒坂", "意识复制"],
            "强尼银手": ["johnny silverhand"],
            "亚当重锤": ["adam smasher"],
            "那首歌": ["i really want to stay at your house", "body heat radio"],
            "电台": ["body heat radio", "98.7", "radioport"],
            "鸣潮": ["边缘幻梦", "somnoire", "night city", "联动", "lucy", "rebecca"],
        }
        self.stopwords = {
            "的", "了", "呢", "吗", "呀", "啊", "我", "想", "请问", "一下", "怎么", "怎样",
            "是否", "一个", "这个", "那个", "可以", "需要", "有没有", "如何",
            "什么", "为什么", "介绍", "讲讲", "相关", "资料", "知识库",
        }

    def _init_chain(self):
        """构造“提示词 -> 模型 -> 文本解析”的最小总结链。"""
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def _ensure_collection_ready(self):
        """
        向量库为空时自动触发一次本地知识入库，避免首次使用直接空检索。
        """
        if self._collection_ready_checked:
            return
        self._collection_ready_checked = True

        try:
            current_count = self.vector_store.vector_store._collection.count()
        except Exception as e:
            logger.error(f"获取向量库文档数量失败: {str(e)}", exc_info=True)
            return

        if current_count > 0:
            logger.info(f"当前向量库已有文档，数量: {current_count}")
            return

        logger.warning("检测到向量库为空，开始自动加载知识文档")
        try:
            self.vector_store.load_document()
            latest_count = self.vector_store.vector_store._collection.count()
            logger.info(f"自动加载完成，当前向量库文档数量: {latest_count}")
        except Exception as e:
            logger.error(f"自动加载知识文档失败: {str(e)}", exc_info=True)

    @staticmethod
    def _is_corrupted_index_error(error: Exception) -> bool:
        message = str(error).lower()
        return (
            "hnsw segment reader" in message
            or "nothing found on disk" in message
            or "error executing plan" in message
        )

    def _repair_vector_store(self):
        """在检测到索引损坏时，串行重建向量库，避免并发修复。"""
        with self._repair_lock:
            logger.warning("检测到向量索引异常，开始重建向量库")
            self.vector_store.reset_store(clear_md5=True)
            self.vector_store.load_document(force_reload=True)
            self._bm25_cache = None
            self._collection_ready_checked = True
            latest_count = self.vector_store.get_collection_count()
            logger.info(f"向量库重建完成，当前文档数量: {latest_count}")

    @staticmethod
    def _normalize_query(query: str) -> str:
        """对用户问题做轻量规范化，统一一些常见别名。"""
        normalized = re.sub(r"\s+", " ", query.strip().lower())
        replacements = {
            "cyberpunk: edgerunners": "cyberpunk edgerunners",
            "cyberpunk edgerunner": "cyberpunk edgerunners",
            "赛博朋克 边缘行者": "赛博朋克边缘行者",
            "赛博朋克：边缘行者": "赛博朋克边缘行者",
            "赛博朋克2077": "cyberpunk 2077",
            "2077": "cyberpunk 2077",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized

    def _expand_query(self, query: str) -> str:
        """把口语化问题扩展成更适合检索的表达。"""
        normalized = self._normalize_query(query)
        expansions = []
        episode_titles = {
            1: "第01集 let you down 令人失望",
            2: "第02集 like a boy 假小子",
            3: "第03集 smooth criminal 犯罪高手",
            4: "第04集 lucky you 算你走运",
            5: "第05集 all eyez on me 众目睽睽",
            6: "第06集 girl on fire 烈火之女 曼恩 崩溃 赛博精神病 转折点",
            7: "第07集 stronger 更加强大 大卫 接任 团队 升级",
            8: "第08集 stay 留下 露西 荒坂 公司阴谋",
            9: "第09集 humanity 人性 陷阱 赛博骨架",
            10: "第10集 my moon my man 我的月亮我的人 结局 月球 亚当重锤",
        }
        for match in re.finditer(r"第\s*(\d{1,2})\s*集", normalized):
            episode_number = int(match.group(1))
            if episode_number in episode_titles:
                expansions.append(episode_titles[episode_number])
        for phrase, candidates in self.synonym_map.items():
            if phrase in normalized:
                expansions.extend(candidates)
        if expansions:
            normalized = f"{normalized} {' '.join(expansions)}"
        return normalized

    def _query_terms(self, query: str) -> set[str]:
        """提取检索关键词，供后续重排计算覆盖率。"""
        expanded = self._expand_query(query)
        terms = set()
        for term in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]+", expanded):
            if term not in self.stopwords:
                terms.add(term)
        return terms

    @staticmethod
    def _document_terms(content: str) -> set[str]:
        """把文档内容切成词项集合，便于和 query 做简单交集比较。"""
        normalized = content.lower()
        terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]+", normalized))
        compact = re.sub(r"\s+", "", normalized)
        if re.search(r"[\u4e00-\u9fff]", compact):
            for size in (2, 3, 4):
                terms.update(compact[index:index + size] for index in range(0, max(len(compact) - size + 1, 0)))
        return terms

    def _tokenize_for_bm25(self, text: str) -> list[str]:
        """
        面向中英混合知识库的 BM25 分词。

        jieba 负责中文自然分词；英文/数字按词切分；中文再补充 2/3/4 字 n-gram，
        避免专有名词未进词典时被切碎后召回不稳。
        """
        normalized = text.lower()
        tokens = [
            token.strip()
            for token in jieba.lcut(normalized)
            if token.strip() and token.strip() not in self.stopwords and re.search(r"[\u4e00-\u9fffA-Za-z0-9]", token)
        ]
        for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]+", normalized):
            if token not in self.stopwords:
                tokens.append(token)

        compact = re.sub(r"[^\u4e00-\u9fff]+", "", normalized)
        for size in (2, 3, 4):
            for index in range(0, max(len(compact) - size + 1, 0)):
                gram = compact[index:index + size]
                if gram not in self.stopwords:
                    tokens.append(gram)
        return tokens

    def _get_bm25_cache(self):
        """构建并缓存 bm25s 索引；向量库文档数量变化时自动重建。"""
        try:
            collection_count = self.vector_store.get_collection_count()
        except Exception:
            collection_count = None

        if self._bm25_cache and self._bm25_cache.get("collection_count") == collection_count:
            return self._bm25_cache

        with self._bm25_lock:
            if self._bm25_cache and self._bm25_cache.get("collection_count") == collection_count:
                return self._bm25_cache

            try:
                stored = self.vector_store.vector_store.get(include=["documents", "metadatas"])
            except Exception as e:
                logger.warning(f"BM25读取向量库失败: {str(e)}")
                return None

            docs = []
            tokenized_corpus = []
            documents = stored.get("documents") or []
            metadatas = stored.get("metadatas") or []
            for content, metadata in zip(documents, metadatas):
                if not content:
                    continue
                doc = Document(page_content=content, metadata=dict(metadata or {}))
                if not self._is_current_domain_doc(doc):
                    continue
                tokens = self._tokenize_for_bm25(content)
                if not tokens:
                    continue
                docs.append(doc)
                tokenized_corpus.append(tokens)

            if not docs:
                self._bm25_cache = {
                    "collection_count": collection_count,
                    "docs": [],
                    "retriever": None,
                }
                return self._bm25_cache

            retriever = bm25s.BM25(k1=self.bm25_k1, b=self.bm25_b)
            retriever.index(tokenized_corpus, show_progress=False)
            self._bm25_cache = {
                "collection_count": collection_count,
                "docs": docs,
                "retriever": retriever,
            }
            logger.info(f"BM25索引构建完成，文档数={len(docs)}，collection_count={collection_count}")
            return self._bm25_cache

    def _bm25_search_docs(self, query: str, limit: int) -> list[tuple[Document, float]]:
        """使用 bm25s 对 Chroma 已存文档做关键词召回，作为 dense embedding 的互补通道。"""
        query_tokens = self._tokenize_for_bm25(self._expand_query(query))
        if not query_tokens:
            return []
        cache = self._get_bm25_cache()
        if not cache or not cache.get("retriever") or not cache.get("docs"):
            return []

        result = cache["retriever"].retrieve([query_tokens], k=limit, show_progress=False)
        scored_docs = []
        for doc_index, score in zip(result.documents[0], result.scores[0]):
            score = float(score)
            if score <= 0:
                continue
            doc = cache["docs"][int(doc_index)]
            doc.metadata["bm25_score"] = round(score, 4)
            scored_docs.append((doc, score))
        return scored_docs

    @staticmethod
    def _source_text(doc: Document) -> str:
        return str((doc.metadata or {}).get("source", "")).lower()

    def _is_current_domain_doc(self, doc: Document) -> bool:
        """当前助手只服务 Cyberpunk 知识库，过滤历史残留的其他主题资料。"""
        source = self._source_text(doc)
        return "cyberpunk_edgerunners_rag_kb_pack" in source

    def _source_route_boost(self, query: str, doc: Document) -> float:
        """按问题类型提升更可信的专题资料，避免通用合集或无关文件抢占 top-k。"""
        normalized = self._normalize_query(query)
        source = self._source_text(doc)
        boost = 0.0

        if re.search(r"第\s*\d{1,2}\s*集|episode|ep\s*\d{1,2}", normalized):
            if any(name in source for name in ("01_作品基础", "03_赛博朋克边缘行者100问", "cyberpunk_edgerunners_full_kb")):
                boost += 0.22
        if any(term in normalized for term in ("大卫", "露西", "丽贝卡", "瑞贝卡", "曼恩", "琦薇", "琪薇", "亚当重锤", "角色", "人物")):
            if any(name in source for name in ("05_人物关系", "03_赛博朋克边缘行者100问", "cyberpunk_edgerunners_full_kb")):
                boost += 0.22
        if any(term in normalized for term in ("斯安威斯坦", "沙德维斯坦", "义体", "赛博精神病", "荒坂", "夜之城", "relic", "soulkiller")):
            if any(name in source for name in ("04_夜之城", "06_设定术语", "08_游戏本体", "cyberpunk_edgerunners_full_kb")):
                boost += 0.18
        if any(term in normalized for term in ("歌", "电台", "radio", "body heat", "i really want")):
            if "08_游戏本体" in source or "cyberpunk_edgerunners_full_kb" in source:
                boost += 0.22
        if any(term in normalized for term in ("鸣潮", "联动", "复活", "正史", "边缘幻梦", "somnoire")):
            if "09_鸣潮" in source or "cyberpunk_edgerunners_full_kb" in source:
                boost += 0.22

        if "\\pdf\\" in source:
            boost -= 0.04
        return boost

    @staticmethod
    def _content_fingerprint(content: str) -> str:
        compact = re.sub(r"\s+", "", content.lower())
        return compact[:180]

    def _select_diverse_docs(self, scored_docs: list[tuple[Document, float]]) -> list[Document]:
        """先按分数排序，再控制重复来源和重复内容，给模型更多互补上下文。"""
        selected = []
        seen_content = set()
        source_counts = {}
        max_per_source = 2

        for doc, _ in scored_docs:
            source = doc.metadata.get("source", "unknown")
            fingerprint = self._content_fingerprint(doc.page_content)
            if fingerprint in seen_content:
                continue
            if source_counts.get(source, 0) >= max_per_source:
                continue
            selected.append(doc)
            seen_content.add(fingerprint)
            source_counts[source] = source_counts.get(source, 0) + 1
            if len(selected) >= self.top_k:
                return selected

        for doc, _ in scored_docs:
            if doc in selected:
                continue
            fingerprint = self._content_fingerprint(doc.page_content)
            if fingerprint in seen_content:
                continue
            selected.append(doc)
            seen_content.add(fingerprint)
            if len(selected) >= self.top_k:
                break
        return selected

    @staticmethod
    def _doc_key(doc: Document) -> tuple:
        metadata = doc.metadata or {}
        return (
            metadata.get("source"),
            metadata.get("page"),
            metadata.get("chunk_index"),
            doc.page_content[:80],
        )

    def _merge_by_rrf(
        self,
        query: str,
        dense_candidates: list[tuple[Document, float]],
        bm25_candidates: list[tuple[Document, float]],
    ) -> list[tuple[Document, float]]:
        """使用 Reciprocal Rank Fusion 融合 dense embedding 和 BM25 两路排名。"""
        merged = {}

        def add_ranked(channel: str, ranked_docs: list[tuple[Document, float]], weight: float = 1.0) -> None:
            for rank, (doc, score) in enumerate(ranked_docs, start=1):
                if not self._is_current_domain_doc(doc):
                    continue
                key = self._doc_key(doc)
                if key not in merged:
                    merged[key] = {"doc": doc, "rrf": 0.0}
                target = merged[key]
                target["rrf"] += weight / (self.rrf_k + rank)
                if channel == "dense":
                    target["doc"].metadata["dense_rank"] = rank
                    target["doc"].metadata["dense_score"] = round(float(score), 4)
                elif channel == "bm25":
                    target["doc"].metadata["bm25_rank"] = rank
                    target["doc"].metadata["bm25_score"] = round(float(score), 4)

        dense_ranked = [
            (doc, score)
            for doc, score in dense_candidates
            if score >= self.min_relevance_score and self._is_current_domain_doc(doc)
        ]
        bm25_ranked = [(doc, score) for doc, score in bm25_candidates if self._is_current_domain_doc(doc)]
        add_ranked("dense", dense_ranked)
        add_ranked("bm25", bm25_ranked)

        scored_docs = []
        for item in merged.values():
            doc = item["doc"]
            rrf_score = float(item["rrf"])
            final_score = rrf_score + self._source_route_boost(query, doc) * 0.05
            doc.metadata["rrf_score"] = round(rrf_score, 6)
            doc.metadata["rerank_score"] = round(float(final_score), 6)
            scored_docs.append((doc, final_score))

        scored_docs.sort(key=lambda item: item[1], reverse=True)
        return scored_docs

    def _get_cross_encoder_model(self):
        """Lazy-load Cross-Encoder reranker; dependency/model errors fall back to RRF."""
        if not self.cross_encoder_enabled or self._cross_encoder_unavailable:
            return None
        if self._cross_encoder_model is not None:
            return self._cross_encoder_model

        with self._cross_encoder_lock:
            if self._cross_encoder_model is not None:
                return self._cross_encoder_model
            if self._cross_encoder_unavailable:
                return None
            try:
                from sentence_transformers import CrossEncoder

                self._cross_encoder_model = CrossEncoder(self.cross_encoder_model_name)
                logger.info(f"Cross-Encoder Rerank模型加载完成: {self.cross_encoder_model_name}")
                return self._cross_encoder_model
            except Exception as e:
                self._cross_encoder_unavailable = True
                logger.warning(
                    f"Cross-Encoder Rerank不可用，已回退到RRF结果: {str(e)}"
                )
                return None

    def _cross_encoder_rerank(self, query: str, scored_docs: list[tuple[Document, float]]) -> list[tuple[Document, float]]:
        """Use Cross-Encoder to rerank top RRF candidates when the optional model is available."""
        if not self.cross_encoder_enabled or not scored_docs:
            return scored_docs
        model = self._get_cross_encoder_model()
        if model is None:
            return scored_docs

        rerank_count = min(self.cross_encoder_top_n, len(scored_docs))
        head = scored_docs[:rerank_count]
        tail = scored_docs[rerank_count:]
        pairs = [[query, doc.page_content] for doc, _ in head]
        try:
            scores = model.predict(pairs)
        except Exception as e:
            logger.warning(f"Cross-Encoder Rerank执行失败，已回退到RRF结果: {str(e)}")
            return scored_docs

        reranked_head = []
        for (doc, rrf_score), cross_score in zip(head, scores):
            cross_score = float(cross_score)
            doc.metadata["cross_encoder_score"] = round(cross_score, 6)
            doc.metadata["pre_rerank_score"] = doc.metadata.get("rerank_score", round(float(rrf_score), 6))
            doc.metadata["rerank_score"] = round(cross_score, 6)
            reranked_head.append((doc, cross_score))

        reranked_head.sort(key=lambda item: item[1], reverse=True)
        logger.info(
            f"Cross-Encoder Rerank完成，模型={self.cross_encoder_model_name}，候选数={rerank_count}"
        )
        return reranked_head + tail

    def retriever_docs(self, query):
        """执行检索主流程：查询扩展 -> Dense + BM25 -> RRF -> Cross-Encoder可选精排 -> 多样性截断。"""
        self._ensure_collection_ready()
        expanded_query = self._expand_query(query)
        try:
            candidates = self.vector_store.vector_store.similarity_search_with_relevance_scores(
                expanded_query,
                k=self.candidate_k,
            )
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}", exc_info=True)
            if self._is_corrupted_index_error(e):
                try:
                    self._repair_vector_store()
                    candidates = self.vector_store.vector_store.similarity_search_with_relevance_scores(
                        expanded_query,
                        k=self.candidate_k,
                    )
                except Exception as repair_error:
                    logger.error(f"重建后检索仍失败: {str(repair_error)}", exc_info=True)
                    return []
            else:
                return []

        bm25_candidates = self._bm25_search_docs(query, self.candidate_k)
        scored_docs = self._merge_by_rrf(query, candidates, bm25_candidates)
        scored_docs = self._cross_encoder_rerank(query, scored_docs)
        docs = self._select_diverse_docs(scored_docs)
        logger.info(
            f"RAG检索完成，原始query={query}，扩展query={expanded_query}，"
            f"向量候选数={len(candidates)}，BM25候选数={len(bm25_candidates)}，融合候选数={len(scored_docs)}，入选数={len(docs)}"
        )
        return docs

    @staticmethod
    def _format_references(docs) -> str:
        """把命中的来源整理成回答尾部可展示的引用列表。"""
        references = []
        seen = set()
        for doc in docs:
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page")
            ref = f"{source} 第{page + 1}页" if isinstance(page, int) else source
            if ref not in seen:
                seen.add(ref)
                references.append(ref)
        if not references:
            return ""
        return "\n参考来源：\n- " + "\n- ".join(references)

    def rag_summarize(self, query):
        """对外暴露的 RAG 总入口，返回“总结结果 + 引用来源”。"""
        try:
            context_docs = self.retriever_docs(query)
        except Exception as e:
            logger.error(f"RAG检索流程异常: {str(e)}", exc_info=True)
            return "知识库检索暂时不可用，请稍后重试。"

        if not context_docs:
            return "未检索到相关参考资料。"

        # 把命中文档拼成可追踪来源的上下文，便于模型总结时引用。
        context_parts = []
        for counter, doc in enumerate(context_docs, start=1):
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page")
            chunk_index = doc.metadata.get("chunk_index")
            location_parts = [f"来源={source}"]
            if page is not None:
                location_parts.append(f"页码={page}")
            if chunk_index is not None:
                location_parts.append(f"切片={chunk_index}")
            context_parts.append(
                f"[参考资料{counter}] {' | '.join(location_parts)}\n{doc.page_content.strip()}"
            )
        context = "\n\n".join(context_parts)
        try:
            answer = self.chain.invoke(
                {
                    "input": query,
                    "context": context,
                }
            )
            return answer.strip() + self._format_references(context_docs)
        except Exception as e:
            logger.error(f"RAG总结失败: {str(e)}", exc_info=True)
            return "知识总结暂时不可用，请稍后重试。"


if __name__ == '__main__':
    rag = RagSummarizeService()
    print(rag.rag_summarize("没玩过 Cyberpunk 2077 能看边缘行者吗？"))
