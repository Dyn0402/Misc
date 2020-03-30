# -*- mode: python -*-

block_cipher = None


a = Analysis(['bubs_voter_sel.py'],
             pathex=['/home/dylan/PycharmProjects/Misc'],
             binaries=[('/home/dylan/Software/Web_Driver/chromedriver_linux64/chromedriver', '**.\\selenium\\webdriver**')],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='createEVIPOrg_Automation_new',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='**scriptname**')