# -*- coding: utf-8 -*-
"""生成答辩 PPT（通俗易懂、功能全覆盖），输出到桌面。汇报人：杨晓旭"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# 桌面路径（兼容中文「桌面」）
_HOME = Path.home()
DESKTOP = _HOME / "Desktop"
if not DESKTOP.is_dir():
    DESKTOP = _HOME / "桌面"
OUT = DESKTOP / "企业多租户智能知识库-答辩-杨晓旭.pptx"

C_PRIMARY = RGBColor(0x0F, 0x4C, 0x81)
C_ACCENT = RGBColor(0x0E, 0xA5, 0xE9)
C_BG = RGBColor(0xF1, 0xF5, 0xF9)
C_TEXT = RGBColor(0x1E, 0x29, 0x3B)
C_MUTED = RGBColor(0x64, 0x74, 0x8B)
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_LINE = RGBColor(0xE2, 0xE8, 0xF0)

W = Inches(13.333)
H = Inches(7.5)
MARGIN = Inches(0.55)
HEADER_H = Inches(1.05)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = W
        self.prs.slide_height = H
        self.page = 0
        self.blank = self.prs.slide_layouts[6]

    def save(self):
        DESKTOP.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(OUT))
        print(OUT)

    def _slide(self):
        self.page += 1
        return self.prs.slides.add_slide(self.blank)

    def _rect(self, slide, l, t, w, h, fill, line=None):
        sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
        sh.line.fill.background()
        if line:
            sh.line.color.rgb = line
            sh.line.width = Pt(1)
        return sh

    def _text(
        self,
        slide,
        l,
        t,
        w,
        h,
        text,
        *,
        size=18,
        bold=False,
        color=C_TEXT,
        align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP,
    ):
        box = slide.shapes.add_textbox(l, t, w, h)
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = "微软雅黑"
        p.alignment = align
        return tf

    def _footer(self, slide):
        self._text(
            slide,
            MARGIN,
            H - Inches(0.42),
            Inches(8),
            Inches(0.3),
            "企业多租户智能知识库  ·  汇报人：杨晓旭",
            size=11,
            color=C_MUTED,
        )
        self._text(
            slide,
            W - Inches(1.2),
            H - Inches(0.42),
            Inches(0.8),
            Inches(0.3),
            str(self.page),
            size=11,
            color=C_MUTED,
            align=PP_ALIGN.RIGHT,
        )

    def _header(self, slide, title: str):
        self._rect(slide, 0, 0, W, HEADER_H, C_PRIMARY)
        self._text(slide, MARGIN, Inches(0.28), Inches(12), Inches(0.55), title, size=24, bold=True, color=C_WHITE)

    def _card_grid(self, slide, cards, top=Inches(1.35), cols=2, ch=Inches(2.2)):
        cw = (W - MARGIN * 2 - Inches(0.35)) / cols
        for i, (tag, head, body) in enumerate(cards):
            col, row = i % cols, i // cols
            l = MARGIN + col * (cw + Inches(0.35))
            t = top + row * (ch + Inches(0.22))
            self._rect(slide, l, t, cw, ch, C_WHITE, C_LINE)
            self._rect(slide, l, t, cw, Inches(0.4), C_BG)
            self._text(slide, l + Inches(0.2), t + Inches(0.06), Inches(2), Inches(0.3), tag, size=12, bold=True, color=C_ACCENT)
            self._text(slide, l + Inches(0.2), t + Inches(0.5), cw - Inches(0.4), Inches(0.4), head, size=18, bold=True, color=C_TEXT)
            self._text(slide, l + Inches(0.2), t + Inches(1.0), cw - Inches(0.4), ch - Inches(1.15), body, size=14, color=C_MUTED)

    def feature_table_slide(self, header: str, intro: str, rows: list[tuple[str, str, str]]):
        s = self._slide()
        self._header(s, header)
        self._text(s, MARGIN, Inches(1.18), Inches(12), Inches(0.4), intro, size=14, color=C_MUTED)
        y = Inches(1.62)
        self._rect(s, MARGIN, y, W - MARGIN * 2, Inches(0.4), C_BG)
        cols = [Inches(2.1), Inches(5.4), Inches(4.7)]
        x = MARGIN + Inches(0.12)
        for i, h in enumerate(["功能", "一句话说明", "你会看到什么"]):
            self._text(s, x, y + Inches(0.05), cols[i], Inches(0.32), h, size=13, bold=True, color=C_PRIMARY)
            x += cols[i]
        y += Inches(0.45)
        for name, what, see in rows:
            rh = Inches(0.7)
            self._rect(s, MARGIN, y, W - MARGIN * 2, rh, C_WHITE, C_LINE)
            x = MARGIN + Inches(0.12)
            self._text(s, x, y + Inches(0.12), cols[0], Inches(0.5), name, size=14, bold=True, color=C_TEXT)
            x += cols[0]
            self._text(s, x, y + Inches(0.1), cols[1], Inches(0.55), what, size=13, color=C_TEXT)
            x += cols[1]
            self._text(s, x, y + Inches(0.1), cols[2], Inches(0.55), see, size=12, color=C_MUTED)
            y += rh + Inches(0.06)
            if y > Inches(6.7):
                break
        self._footer(s)

    # ---------- pages ----------
    def cover(self):
        s = self._slide()
        self._rect(s, 0, 0, Inches(4.8), H, C_PRIMARY)
        self._text(s, Inches(0.6), Inches(1.9), Inches(3.8), Inches(2.2), "企业多租户\n智能知识库", size=36, bold=True, color=C_WHITE)
        self._text(s, Inches(0.6), Inches(4.3), Inches(3.6), Inches(0.4), "项目答辩汇报", size=16, color=RGBColor(0xBA, 0xE6, 0xFD))
        self._text(s, Inches(0.6), Inches(5.0), Inches(3.6), Inches(0.9), "汇报人：杨晓旭\n面向：答辩评委 / 老师", size=15, color=C_WHITE)
        self._text(
            s,
            Inches(5.3),
            Inches(2.1),
            Inches(7.3),
            Inches(1.1),
            "把企业文档变成\n「能搜、能问、能核对来源」的知识助手",
            size=26,
            bold=True,
            color=C_PRIMARY,
        )
        for i, line in enumerate(
            [
                "一家平台，服务多家企业（多租户隔离）",
                "员工用大白话提问，AI 按本公司文档作答",
                "平台管开户配额，企业管人管库管问答",
            ]
        ):
            y = Inches(3.6) + Inches(0.55) * i
            self._rect(s, Inches(5.3), y + Inches(0.08), Inches(0.12), Inches(0.28), C_ACCENT)
            self._text(s, Inches(5.55), y, Inches(7), Inches(0.45), line, size=16, color=C_TEXT)
        self._text(
            s,
            Inches(5.3),
            H - Inches(0.75),
            Inches(7.5),
            Inches(0.35),
            "技术栈：FastAPI · Vue3 · RAG · 通义千问 · BGE · Chroma",
            size=12,
            color=C_MUTED,
        )

    def toc(self):
        s = self._slide()
        self._header(s, "目录 · 今天讲什么")
        items = [
            ("01", "项目背景", "为什么做、解决什么问题"),
            ("02", "角色说明", "平台超管 / 企业管理员 / 员工"),
            ("03", "功能全景", "每个功能是干什么的（好理解版）"),
            ("04", "技术与安全", "怎么实现、怎么隔离"),
            ("05", "演示与总结", "答辩怎么操作、收尾"),
        ]
        y = Inches(1.4)
        for num, title, sub in items:
            self._rect(s, MARGIN, y, W - MARGIN * 2, Inches(0.95), C_WHITE, C_LINE)
            self._rect(s, MARGIN, y, Inches(1.0), Inches(0.95), C_BG)
            self._text(s, MARGIN + Inches(0.2), y + Inches(0.28), Inches(0.7), Inches(0.45), num, size=22, bold=True, color=C_ACCENT)
            self._text(s, MARGIN + Inches(1.25), y + Inches(0.18), Inches(5), Inches(0.4), title, size=20, bold=True, color=C_TEXT)
            self._text(s, MARGIN + Inches(1.25), y + Inches(0.55), Inches(8), Inches(0.3), sub, size=14, color=C_MUTED)
            y += Inches(1.05)
        self._footer(s)

    def section(self, num: str, title: str, subtitle: str = ""):
        s = self._slide()
        self._rect(s, 0, 0, W, H, C_PRIMARY)
        self._text(s, MARGIN, Inches(2.35), Inches(4), Inches(0.7), num, size=48, bold=True, color=RGBColor(0x7D, 0xD3, 0xFC))
        self._text(s, MARGIN, Inches(3.15), Inches(11), Inches(0.9), title, size=38, bold=True, color=C_WHITE)
        if subtitle:
            self._text(s, MARGIN, Inches(4.25), Inches(11), Inches(0.5), subtitle, size=18, color=RGBColor(0xBA, 0xE6, 0xFD))
        self._text(s, MARGIN, H - Inches(0.7), Inches(8), Inches(0.35), "汇报人：杨晓旭", size=14, color=RGBColor(0xE0, 0xF2, 0xFE))

    def problem(self):
        s = self._slide()
        self._header(s, "01  这个项目解决什么问题？")
        self._card_grid(
            s,
            [
                ("痛点", "资料难找", "制度、手册、产品说明散落在网盘和邮件里，新人入职要问人、翻文件。"),
                ("目标", "会「答」题", "员工用自然语言提问，系统只根据本企业已上传文档来回答。"),
                ("关键", "能核对", "回答旁边有「引用」，点开能看到来自哪份文档、哪一段。"),
                ("形态", "多租户 SaaS", "一套系统服务多家公司；A 公司看不到 B 公司的资料。"),
            ],
            top=Inches(1.3),
        )
        self._footer(s)

    def roles(self):
        s = self._slide()
        self._header(s, "02  三类人 · 各用哪个入口？")
        rows = [
            ("平台超管", "平台登录页", "开通/停用/删除企业，设配额与功能开关，看全平台统计", "不管各企业文档正文"),
            ("企业管理员", "租户登录页", "管本企业用户、部门、知识库、文档、看板、审计", "本企业「运营负责人」"),
            ("普通员工", "租户登录页", "选知识库提问、看有权限的库、改自己密码", "日常使用者"),
        ]
        y = Inches(1.3)
        for role, entry, duty, note in rows:
            self._rect(s, MARGIN, y, W - MARGIN * 2, Inches(1.5), C_WHITE, C_LINE)
            self._rect(s, MARGIN, y, Inches(0.1), Inches(1.5), C_ACCENT)
            self._text(s, MARGIN + Inches(0.3), y + Inches(0.15), Inches(2.4), Inches(0.4), role, size=20, bold=True, color=C_PRIMARY)
            self._text(s, MARGIN + Inches(2.8), y + Inches(0.18), Inches(4), Inches(0.35), f"入口：{entry}", size=13, color=C_MUTED)
            self._text(s, MARGIN + Inches(0.3), y + Inches(0.6), Inches(12), Inches(0.4), f"做什么：{duty}", size=15, color=C_TEXT)
            self._text(s, MARGIN + Inches(0.3), y + Inches(1.05), Inches(12), Inches(0.3), note, size=13, color=C_MUTED)
            y += Inches(1.65)
        self._text(
            s,
            MARGIN,
            Inches(6.45),
            Inches(12),
            Inches(0.35),
            "演示账号：platform/platform123　·　admin/admin123　·　employee/employee123",
            size=13,
            color=C_MUTED,
        )
        self._footer(s)

    def onboarding(self):
        s = self._slide()
        self._header(s, "账号从哪来？· 新用户怎么进系统")
        steps = [
            ("① 平台开通企业", "超管在「租户管理」点开通，填写企业名和首任管理员账号密码。"),
            ("② 管理员登录", "用刚设的账号在「租户登录」进入本企业工作台。"),
            ("③ 新增员工", "管理员在「用户管理」里加人，把账号密码发给同事。"),
            ("④ 员工使用", "同事登录后提问；公开库全员可见，私有库需单独授权。"),
        ]
        y = Inches(1.35)
        for title, desc in steps:
            self._rect(s, MARGIN, y, W - MARGIN * 2, Inches(1.15), C_WHITE, C_LINE)
            self._text(s, MARGIN + Inches(0.25), y + Inches(0.15), Inches(12), Inches(0.35), title, size=17, bold=True, color=C_PRIMARY)
            self._text(s, MARGIN + Inches(0.25), y + Inches(0.55), Inches(12), Inches(0.45), desc, size=15, color=C_TEXT)
            y += Inches(1.25)
        self._footer(s)

    def flow(self):
        s = self._slide()
        self._header(s, "03  核心闭环：上传 → 解析 → 提问 → 回答")
        steps = [
            ("① 上传", "把 PDF / Word / Markdown 等资料上传到某个知识库。"),
            ("② 解析", "系统自动切分文字、做成向量，存进向量库。"),
            ("③ 检索", "提问时先找「和问题最相关」的几段原文。"),
            ("④ 生成", "通义千问根据这些片段写答案，并给出引用。"),
        ]
        x = MARGIN
        bw = Inches(2.85)
        for i, (title, desc) in enumerate(steps):
            self._rect(s, x, Inches(1.5), bw, Inches(4.5), C_WHITE, C_LINE)
            self._rect(s, x, Inches(1.5), bw, Inches(0.55), C_PRIMARY)
            self._text(s, x + Inches(0.1), Inches(1.6), bw - Inches(0.2), Inches(0.4), title, size=17, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
            self._text(s, x + Inches(0.2), Inches(2.3), bw - Inches(0.4), Inches(3.4), desc, size=14, color=C_TEXT)
            if i < 3:
                self._text(s, x + bw + Inches(0.02), Inches(3.4), Inches(0.35), Inches(0.4), "→", size=22, bold=True, color=C_ACCENT)
            x += bw + Inches(0.38)
        self._footer(s)

    def platform_feats(self):
        self.feature_table_slide(
            "平台控制台 · 功能一览",
            "给 SaaS 运营方用：管「开几家公司、每家能用多大」，不看各公司文档内容。",
            [
                ("平台登录", "独立入口，与企业账号分开", "platform / platform123"),
                ("平台概览", "看租户数、用户数、文档数、问答量", "运营大盘"),
                ("开通租户", "新建一家企业 + 首任管理员", "相当于「开户」"),
                ("编辑租户", "改联系人、配额、过期时间、启停", "运维与商务配置"),
                ("功能开关", "按企业关闭问答/上传/审计等", "套餐差异化"),
                ("删除租户", "永久删除企业及全部业务数据", "清理测试/退订企业"),
            ],
        )

    def admin_org(self):
        self.feature_table_slide(
            "企业管理员 · 组织与账号",
            "租户登录后侧栏「管理」区：先把人和组织理顺。",
            [
                ("用户管理", "新增/编辑/删除账号，设角色，重置密码", "给同事开登录入口"),
                ("部门管理", "树形部门（顶级/中级/低级）", "方便按部门授权知识库"),
                ("个人设置", "查看身份信息，修改自己的密码", "账号安全"),
            ],
        )

    def admin_kb(self):
        self.feature_table_slide(
            "企业管理员 · 知识库与文档",
            "知识库 = 本企业的「资料文件夹」；文档进库后才能被问答引用。",
            [
                ("知识库列表", "新建、编辑、停用、删除知识库", "卡片式管理"),
                ("租户内公开", "开：全员可见；关：需单独授权", "控制谁能问这份资料"),
                ("权限", "按用户或部门授权「访问/管理」", "私有库精细控权"),
                ("文档管理", "上传、更新、删除、调切片参数", "PDF/Word/Markdown 等"),
                ("解析状态", "成功/失败；失败可去「解析失败」重试", "保证能入库"),
            ],
        )

    def chat_feats(self):
        self.feature_table_slide(
            "AI 问答 · 核心体验（全员相关）",
            "系统最重要的页面：基于所选知识库做智能问答。",
            [
                ("选知识库", "可勾选一个或多个已授权/公开库", "回答范围可控"),
                ("会话列表", "新建、改标题、删除历史对话", "像聊天软件一样管理"),
                ("多轮追问", "同一会话里可接着问「那薪资呢」", "结合上文 + 知识库"),
                ("流式回答", "答案逐段出现，不用干等", "体验更顺畅"),
                ("文档引用", "「查看引用」核对出处", "可溯源、可审计"),
                ("有用/无用", "对回答点赞或踩", "管理员在审计里能看到"),
                ("无关拒答", "问题与库内无关时礼貌说明找不到", "不乱编"),
            ],
        )

    def admin_ops(self):
        self.feature_table_slide(
            "企业管理员 · 统计、审计与运维",
            "管得住、查得清、出了问题能修。",
            [
                ("统计看板", "知识库/文档/问答量、好评差评、失败数", "一眼看健康度"),
                ("问答审计", "查历史问答、筛选、详情、批量删除", "内控留痕"),
                ("导出 CSV", "导出审计记录（平台可关掉此能力）", "归档汇报"),
                ("解析失败", "集中查看失败文档并重新触发解析", "运维兜底"),
            ],
        )

    def employee_feats(self):
        self.feature_table_slide(
            "普通员工 · 能用哪些功能",
            "员工侧菜单更精简：专注提问与看资料。",
            [
                ("AI 问答", "选库提问、多轮对话、看引用、点反馈", "主功能"),
                ("知识库", "只看见公开库或被授权的库", "看不到未授权内容"),
                ("个人设置", "修改登录密码", "基础安全"),
                ("无管理菜单", "没有用户/部门/审计等入口", "职责分离"),
            ],
        )

    def tech(self):
        s = self._slide()
        self._header(s, "04  技术怎么实现（分层）")
        layers = [
            ("展示层", "Vue3 + Element Plus + Vite", "登录、问答、管理界面"),
            ("接口层", "FastAPI + JWT", "REST 接口 + 问答流式输出"),
            ("业务层", "多租户 · 权限 · 配额 · 功能开关", "平台与企业职责分离"),
            ("AI 层", "检索 + 通义千问（RAG）", "先找片段再生成答案"),
            ("数据层", "SQLite/MySQL + Chroma + 文件", "账号数据 · 向量 · 原文件"),
        ]
        y = Inches(1.25)
        for name, tech, note in layers:
            self._rect(s, MARGIN, y, Inches(2.1), Inches(0.88), C_PRIMARY)
            self._text(s, MARGIN + Inches(0.1), y + Inches(0.25), Inches(1.9), Inches(0.4), name, size=15, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
            self._rect(s, MARGIN + Inches(2.25), y, Inches(4.0), Inches(0.88), C_BG)
            self._text(s, MARGIN + Inches(2.4), y + Inches(0.25), Inches(3.7), Inches(0.4), tech, size=14, bold=True, color=C_TEXT)
            self._rect(s, MARGIN + Inches(6.4), y, Inches(5.9), Inches(0.88), C_WHITE, C_LINE)
            self._text(s, MARGIN + Inches(6.55), y + Inches(0.25), Inches(5.6), Inches(0.4), note, size=14, color=C_MUTED)
            y += Inches(1.0)
        self._footer(s)

    def security(self):
        s = self._slide()
        self._header(s, "安全与隔离 · 答辩常问")
        self._card_grid(
            s,
            [
                ("租户隔离", "业务数据都带企业 ID", "A 企业永远看不到 B 企业"),
                ("向量隔离", "检索时过滤企业 + 知识库", "不会串库乱答"),
                ("双入口鉴权", "平台 Token / 租户 Token 分开", "超管密码不能当员工用"),
                ("密码安全", "密码哈希存储，不明文保存", "支持重置与自行修改"),
            ],
            top=Inches(1.3),
        )
        self._footer(s)

    def demo(self):
        s = self._slide()
        self._header(s, "05  答辩现场建议演示顺序（约 8～10 分钟）")
        steps = [
            "1. 租户 admin 登录 → AI 问答：选库提问 → 展开「引用」→ 点有用/无用（核心亮点）",
            "2. 同会话追问一句「那薪资呢？」（展示多轮对话）",
            "3. 知识库：说明「租户内公开 / 需授权」→ 打开文档列表看解析状态",
            "4. 用户管理：说明如何给同事开账号（员工登录菜单更少）",
            "5. 平台超管：开通/编辑租户、功能开关、删除租户（SaaS 运营能力）",
            "6. 可选：统计看板 + 问答审计（可管、可查）",
        ]
        y = Inches(1.25)
        for st in steps:
            self._rect(s, MARGIN, y, W - MARGIN * 2, Inches(0.8), C_WHITE, C_LINE)
            self._text(s, MARGIN + Inches(0.2), y + Inches(0.2), Inches(12.2), Inches(0.5), st, size=15, color=C_TEXT)
            y += Inches(0.88)
        self._footer(s)

    def closing(self):
        s = self._slide()
        self._rect(s, 0, 0, W, H, C_PRIMARY)
        self._text(s, MARGIN, Inches(1.9), Inches(11), Inches(0.7), "总结", size=36, bold=True, color=C_WHITE)
        for i, p in enumerate(
            [
                "多租户：一家平台服务多家企业，数据互不可见",
                "全流程：上传文档 → 解析入库 → 智能问答 → 引用溯源",
                "三分角色：平台运营、企业治理、员工日常提问",
                "可运营：配额、功能开关、审计、失败重试、删除租户",
            ]
        ):
            self._text(s, MARGIN + Inches(0.2), Inches(2.8) + Inches(0.55) * i, Inches(11), Inches(0.45), "▸  " + p, size=18, color=RGBColor(0xE0, 0xF2, 0xFE))
        self._text(s, MARGIN, Inches(5.4), Inches(11), Inches(0.55), "感谢聆听 · 欢迎提问", size=28, bold=True, color=C_WHITE)
        self._text(s, MARGIN, Inches(6.2), Inches(11), Inches(0.4), "汇报人：杨晓旭", size=16, color=RGBColor(0xBA, 0xE6, 0xFD))


def main():
    d = Deck()
    d.cover()
    d.toc()
    d.section("PART 01", "背景与角色", "先讲清楚：为什么做、谁在用")
    d.problem()
    d.roles()
    d.onboarding()
    d.section("PART 02", "功能说明", "每个模块用大白话讲清楚")
    d.flow()
    d.platform_feats()
    d.admin_org()
    d.admin_kb()
    d.chat_feats()
    d.admin_ops()
    d.employee_feats()
    d.section("PART 03", "技术与安全", "怎么做出来、怎么隔离")
    d.tech()
    d.security()
    d.section("PART 04", "演示与收尾", "现场怎么讲、怎么收")
    d.demo()
    d.closing()
    d.save()


if __name__ == "__main__":
    main()
