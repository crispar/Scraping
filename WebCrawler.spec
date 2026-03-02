# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=['crawler.parsers.analyticsindiamag_parser', 'crawler.parsers.androidpolice_parser', 'crawler.parsers.arstechnica_parser', 'crawler.parsers.axios_parser', 'crawler.parsers.businessinsider_parser', 'crawler.parsers.cnbc_parser', 'crawler.parsers.datacenterknowledge_parser', 'crawler.parsers.deadline_parser', 'crawler.parsers.dexerto_parser', 'crawler.parsers.economist_parser', 'crawler.parsers.engadget_parser', 'crawler.parsers.fortune_parser', 'crawler.parsers.fourzerofour_parser', 'crawler.parsers.gamespot_parser', 'crawler.parsers.generic_parser', 'crawler.parsers.giveupinternet_parser', 'crawler.parsers.gizmodo_parser', 'crawler.parsers.google_research_parser', 'crawler.parsers.interviewquery_parser', 'crawler.parsers.marktechpost_parser', 'crawler.parsers.naver_blog_parser', 'crawler.parsers.naver_news_parser', 'crawler.parsers.nbc_news_parser', 'crawler.parsers.ninetofivegoogle_parser', 'crawler.parsers.nltimes_parser', 'crawler.parsers.openai_parser', 'crawler.parsers.pcgamer_parser', 'crawler.parsers.reddit_parser', 'crawler.parsers.restofworld_parser', 'crawler.parsers.samaltman_parser', 'crawler.parsers.sammobile_parser', 'crawler.parsers.scmp_parser', 'crawler.parsers.sfgate_parser', 'crawler.parsers.substack_parser', 'crawler.parsers.techafricanews_parser', 'crawler.parsers.techcrunch_parser', 'crawler.parsers.technically_parser', 'crawler.parsers.thedrive_parser', 'crawler.parsers.thehindu_parser', 'crawler.parsers.tomshardware_parser', 'crawler.parsers.towardsdatascience_parser', 'crawler.parsers.upperclasscareer_parser', 'crawler.parsers.verge_parser', 'crawler.parsers.wired_parser', 'crawler.parsers.zmescience_parser', 'PIL._tkinter_finder', 'babel.numbers'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WebCrawler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
