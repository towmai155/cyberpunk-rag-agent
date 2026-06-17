# 赛博朋克：边缘行者 RAG 知识库包

生成日期：2026-06-16

## 文件说明
- 01_作品基础与观看指南.txt/pdf：基础资料、观看顺序、剧透等级、分集索引。
- 02_剧情疑问排除.txt/pdf：模仿“故障排除”的观看问题排查库。
- 03_赛博朋克边缘行者100问.txt/pdf：项目演示最适合用的 FAQ。
- 04_夜之城世界观与设定.txt/pdf：夜之城、公司、义体、职业、主题设定。
- 05_人物关系与角色解析.txt/pdf：大卫、露西、丽贝卡、曼恩、琦薇、法拉第、亚当重锤等。
- 06_设定术语与义体系统.txt/pdf：术语解释与同义词索引。
- 07_推荐避雷与RAG项目设计.txt/pdf：推荐规则、避雷标签、RAG 入库策略。
- cyberpunk_edgerunners_full_kb.txt/pdf：完整合集。
- cyberpunk_edgerunners_rag_chunks.jsonl：一行一个 chunk，可直接入向量库。

## 资料来源类型
本包基于公开网页做原创摘要整理，没有整页复制网页内容。主要参考：
- Bangumi：条目、话数、制作人员、分集、评分与标签快照。
- Cyberpunk 官方站 / Netflix Media Center：故事定位、角色与制作信息。
- Cyberpunk Wiki / Fandom：斯安威斯坦、赛博精神病等设定术语。
- 萌娘百科：角色中文资料与角色条目导航。
- CD PROJEKT RED：Edgerunners 2 与 MADNESS 漫画前传公开信息。

## 使用建议
1. 把 JSONL 的 retrieval_text 用于 embedding。
2. 把 spoiler_level 用作过滤字段。
3. 用户没说明观看进度时，只召回 S0/S1。
4. 问“结局、死亡、亚当重锤、最后一集”时再允许 Full。
5. 角色、术语、集数要保留关键词索引，不要只靠向量。

## 源 URL
- bangumi: https://bangumi.tv/subject/309311
- netflix_media: https://media.netflix.com/en/only-on-netflix/81054853
- official_site: https://www.cyberpunk.net/en/edgerunners
- cdpr_edgerunners2: https://www.cyberpunk.net/en/news/51617/cyberpunk-edgerunners-2-is-now-in-production
- cdpr_madness: https://press.cdprojektred.com/en/news/1717/cyberpunk-edgerunners-receives-a-manga-prequel-and-blu-ray-edition
- cyberpunk_wiki_sandevistan: https://cyberpunk.fandom.com/wiki/Sandevistan
- cyberpunk_wiki_cyberpsychosis: https://cyberpunk.fandom.com/wiki/Cyberpsychosis
- wikipedia_edgerunners: https://en.wikipedia.org/wiki/Cyberpunk:_Edgerunners
- moegirl_category: https://moegirl.icu/Category:%E8%B5%9B%E5%8D%9A%E6%9C%8B%E5%85%8B_%E8%BE%B9%E7%BC%98%E8%A1%8C%E8%80%85
- moegirl_david: https://moegirl.uk/index.php?title=%E5%A4%A7%E5%8D%AB%C2%B7%E9%A9%AC%E4%B8%81%E5%86%85%E6%96%AF&variant=zh-cn
- moegirl_lucy: https://moegirl.uk/index.php?title=%E9%9C%B2%E8%A5%BF%28%E8%B5%9B%E5%8D%9A%E6%9C%8B%E5%85%8B%E8%BE%B9%E7%BC%98%E8%A1%8C%E8%80%85%29&variant=zh-sg
- moegirl_rebecca: https://moegirl.uk/index.php?title=%E4%B8%BD%E8%B4%9D%E5%8D%A1&variant=zh

新增补充模块：
- 08_游戏本体联动与音乐电台：补充 Cyberpunk 2077 游戏本体、强尼银手、V、Relic、亚当重锤、夜之城区域、Phantom Liberty、98.7 Body Heat Radio 与《I Really Want to Stay at Your House》等音乐电台资料。
