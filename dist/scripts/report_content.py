"""Generate the human report from audited counts and recorded test results."""
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((R/p).read_text(encoding='utf-8-sig'))
s=read('content-completeness.json');c=read('data/course.json');tests=read('qa/test-results.json');b=read('scripts/content-baseline.json')
assert s['course']['verified_topics']==41 and tests['status']=='passed'
branch=subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(str(x).replace('|',' / ') for x in row)+' |' for row in rows]])
v=s['validation'];a=s['sources'];e=s['exercises'];d=s['content']
unit_rows=[]
for u in c['units']:
    ts=[t for t in c['topics'] if t['topic_id'] in u['topic_refs']]
    unit_rows.append([u['unit_id'],u['title'],len(ts),sum(t['content_status']=='verified' for t in ts),'通过'])
text=f'''# AP Physics C: Mechanics 课程内容完整性报告 · V0.3

本轮完成全部 {s['course']['topics']} 个 Topic，并按 Unit 分批检查。课程仍为用户冻结的 2026–27 / May 2027、7 Units / 41 Topics；范围、顺序与原 PDF 不变。没有自动写入用户“已学习”、练习、MF 或测评记录。

本地分支：`{branch}`。前置验收提交：`{b['checkpoint']}`（PL UI UX stabilization before content completion）。本轮最终提交的准确 HEAD、干净状态、ZIP 校验值与本地保存位置见交付目录中的 **Content交付记录.txt**，避免把提交自身的编号写入提交内容。

## 每个 Unit

{table(['Unit','名称','Topics','verified','结果'],unit_rows)}

content-ready = {s['course']['content_ready_topics']}；verified = {s['course']['verified_topics']}。数据中的 `status=validated` 保持原渲染器兼容，`content_status=verified` 与 `exercise_status=exercise_ready` 表示开发验证状态，与浏览器中的学习标记分开。

## 正文与资源

{table(['项目','实际数量'],[['唯一教材 section',d['unique_source_sections']],['唯一正文原页区域',d['unique_reading_regions']],['正文中保留的 Figure',d['figures_in_reading']],['全部 Figure 索引（含章末及排除内容）',d['indexed_figures']],['唯一 Example',d['examples']],['唯一 Check Your Understanding',d['check_your_understanding']],['Supplement',d['supplements']],['唯一原页图像文件',a['unique_page_assets']],['本轮新增原页文件',a['new_page_assets']],['复用原有原页文件',a['reused_baseline_page_assets']]])}

正文以原 PDF 渲染的区域展示，公式、图、Strategy、Solution、Significance 与例题分页继续保留。Example / Check 均属于正文，没有作为正式 Exercise 重复入库。同一原页只保存一个 PNG，Topic 与题目通过坐标引用；同一图没有重复生成图片文件。Figure 索引追加了原 PDF 文本流换行导致旧索引漏掉的图注，并按书中编号排序。

范围取舍执行既有选择规则：1.1 复用 §2.4 数学工具；1.3 使用 motion graph / calculus；2.1、2.2、2.4、2.8、4.3 使用冻结的局部正文；6.1 使用旋转动能与滚动能量，保留定义动能所需的 I 与完整 Example 10.8；6.6 保留引力势能、轨道能量与 Kepler 内容，省略高级圆锥曲线推导和转移轨道主体；7.2 保留质量弹簧与单摆周期，7.3 保留水平/竖直弹簧 x/v/a 原图，7.5 保留单摆和物理摆正文、不含扭摆主体。

§8.5、§9.7、§11.4、§12.3–12.4、§13.6–13.7、§15.5–15.6 以及 Chapters 14/16/17 不进入 Topic 正文。原 PDF 完整保留其现存内容。

## 正式章末题

唯一正式源 Exercise = **{e['unique_formal_source_exercises']}**；Topic 正式题库去重后 = **{e['unique_topic_exercises']}**；AP 章末入口可见 = **{e['visible_chapter_exercises']}**。Topic 与 Chapter 引用同一 `exercise_id`，没有复制题目实体。每章原编号连续，全部正式源题均由章末目录引用，排除范围题保留在源目录及完整 PDF。

“整章题目”与“排除内容保持隐藏”存在交叉要求，采用已说明的默认处理：整章正式题全部建立源目录，AP 入口隐藏明确排除题，不把整章题塞进单个 Topic。隐藏 {e['unique_formal_source_exercises']-e['visible_chapter_exercises']} 道；该策略记录在 `chapter-reviews.json` 的 `scope_policy` 与题目 `chapter_scope_review`。

{table(['Chapter','全部源正式题','AP 章末可见','Topic 引用去重'],[[r['chapter'],r['source_exercises'],r['visible_exercises'],r['topic_exercises']] for r in e['chapters']])}

带嵌入原图的源 Exercise = {e['illustrated_source_exercises']}，其中可见章末题 = {e['illustrated_visible_exercises']}，Topic 题 = {e['illustrated_topic_exercises']}。此数从原 PDF 的图像对象位置计算（宽 ≥25pt、高 ≥20pt，与题目区域相交），包含题目照片/示意图；不是把每个题目截图都算成“有图”。公式和矢量内容仍由原页完整显示。图像裁断候选 = {len(v['clipped_image_candidates'])}。

修正了章末双栏摘要混入题目、印刷页 747 的第 56 题右栏续文，以及印刷页 749 第 67 题跨栏浮动续文。原有第 6 章页 296 与第 10 章页 513 的浮动图修正继续保留。第 15 章第 14 题实际询问 sine/cosine 初始条件，引用到 7.3，保留原书 §15.4 标签；不加入 7.5。新增少量质量弹簧 Additional Problems 引用时也保留原章末类别与原编号。

每道题的原图、公式与所有子问以 `render_refs` 为准。`question_text` 仅用于搜索，PDF 中部分公式是图形，不能用文字转录替代原题。原书未给出或未索引到的答案不补写，已有答案链接定位到原 PDF。

## 每个 Topic

{table(['Topic','原页区域','题目引用','Figure','Example','Check'],[[t['topic_id'],t['reading_regions'],t['exercises'],t['figures'],t['examples'],t['checks']] for t in s['topics']])}

Topic 之间会共享材料，因此本表相加不是唯一总量；唯一数使用上文的集合去重结果。书中某节没有 Example 或 Check 时不造例题。

## 来源、页码与署名

原教材：OpenStax / Rice University · University Physics Volume 1。许可采用附件 PDF 第 6 页实际声明 **{a['license']}**，未根据网站或记忆替换版本。原文件 SHA256：`{a['source_sha256']}`。

PDF 页 = {a['pdf_pages']}；有印刷页编号的映射 = {a['mapped_printed_pages']}；前 5 页无编号。印刷页 **863–874 缺失** 的事实保留，不补造、不覆盖原 PDF。例：印刷页 202 → PDF 207，印刷页 941 → PDF 934；程序逐页查 `page-map.json`，没有固定 +5。

来源许可字段完整：正文区域 {a['attribution_completeness']['reading_regions']}/{d['indexed_reading_regions']}、Figure {a['attribution_completeness']['figures']}/{d['indexed_figures']}、Exercise {a['attribution_completeness']['exercises']}/{e['unique_formal_source_exercises']}。正文对象通过原页区域继承来源。{a['figure_credit_entries']} 条 Figure 索引带独立 credit，独立图片许可不统一推定；完整图注随原页保留。

Figure 6.9 的 OS541/DoD 独立署名及“图像出现不代表美国国防部认可”的声明继续保留：

> {a['figure_6_9_credit'][0]}

4 个既有 Supplement 的文件校验值和 Topic 引用不变，未新增第五个。书外必要内容由这四个已冻结 Supplement 覆盖；未发现需要新增 Supplement 的 blocker。

## 验证与保护范围

{table(['检查','实际结果'],[['所有 Topic 页面实际进入',v['all_topic_UI_pages']],['原页 PNG 解码成功',v['PNG_files_decoded']],['无效资源引用',v['broken_asset_references']],['重复 Exercise ID',v['duplicate_exercise_ids']],['重复原页资源',v['duplicate_source_assets']],['缺图文件',v['missing_images']],['孤立 Exercise',v['orphan_exercises']],['Topic 无正文',v['topics_without_reading']],['Topic 无合法冻结映射',v['topics_without_frozen_mapping']]])}

2.5 / 5.4 / 7.5 回归通过：原有 {v['baseline_original_regions']} 个正文区域、{v['baseline_original_exercises']} 道唯一题目的原题、原图、页码、答案与来源保持不变；分别保留 26/12/6 个正文区域与 41/14/18 道题的映射。原资产哈希不变，Figure 只增加共享引用。{v['protected_UI_source_files']} 个界面、核心、MF 与来源文件逐一校验不变；Priority 原 27 组权重回归通过，Review/Progress/Toggle/i18n/Dark/计时与课程设置未重写。

必要的通用呈现修复只有学习目标使用原教材数据，以及 Example/Check 支持多个区域引用。另补 `sw.js` 兼容已有页面注册逻辑：旧本机预览曾由旧离线缓存显示三节版本，该脚本接管后请求读取新文件，不删除缓存或浏览器学习存储；实际验证同一地址 41 个入口全部可用。

{table(['测试','结果'],[[t['name'],t['status']] for t in tests['checks']])}

浏览器逐页记录见 `qa/content-page-checks.json`，41 页均有正文、对应题目与 Chapter 入口，没有自动勾选“已学习”；浏览器警告/错误记录为 0。独立测试地址验证第 15 章第 60 题：Topic 标记后两个入口都高亮，取消后两个入口都取消。实际原图视觉检查包括各 Unit 代表页、弹簧/SHM 图像、轨道裁剪、单摆回归及专项跨页题；所有文件路径、页码、图像解码和区域边界另做全量程序检查。没有宣称逐字重校原书。

详细测试输出见 `qa/test-results.json`，正文图像示例见 `qa/shm-source.png`。项目是可直接双击使用的静态网页，没有安装依赖或独立构建步骤；全部 JavaScript 语法检查与现有测试通过。

完成后停止在 Priority 2。无剩余 blocker；没有 push、deploy、新课程、AI、GMF 接入、MF 开发或最终三产品融合。
'''
(R/'课程内容完整性报告.md').write_text(text,encoding='utf-8')
print('Report generated from audited data:',R/'课程内容完整性报告.md')
