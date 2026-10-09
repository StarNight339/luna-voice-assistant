from luna import autostart, shortcut


def test_launcher_bootstrap_runs_in_venv(tmp_path):
    """โค้ด -c ที่ใส่ในทางลัดต้องรันได้จริง: ตั้ง sys.prefix และโหลด site-packages ของ venv"""
    import subprocess
    import sys

    site_packages = tmp_path / "Lib" / "site-packages"
    (site_packages / "luna").mkdir(parents=True)
    (site_packages / "luna" / "__init__.py").touch()
    (site_packages / "luna" / "__main__.py").write_text(
        "import sys\ndef main():\n    print(sys.prefix, sys.argv[0])\n", encoding="utf-8")
    exe, flag, boot = autostart.launcher(tmp_path, sys.base_prefix)
    assert exe.endswith("pythonw.exe") and flag == "-c"
    out = subprocess.run([sys.executable, "-S", "-c", boot], cwd=tmp_path.parent,  # cwd ไม่ใช่ repo: ไม่หยิบ luna ตัวจริง
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == f"{tmp_path} luna"


def test_ps_script_escapes_quotes():
    script = shortcut.ps_script([r"C:\Users\O'Neil\Desktop\Luna.lnk"], [r"C:\p\pythonw.exe", "-m", "luna"],
                                r"C:\p", r"C:\p\luna.ico")
    assert r"CreateShortcut('C:\Users\O''Neil\Desktop\Luna.lnk')" in script
    assert "$s.Arguments = '-m luna'" in script
    assert script.count("$s.Save()") == 1


def test_ps_script_without_arguments():
    script = shortcut.ps_script([r"C:\d\Luna.lnk"], [r"C:\p\app.exe"], r"C:\p", r"C:\p\luna.ico")
    assert r"$s.TargetPath = 'C:\p\app.exe'" in script
    assert "$s.Arguments = ''" in script


def test_locations_are_start_menu_and_desktop():
    start_menu, desktop = shortcut.locations()
    assert start_menu.name == desktop.name == "Luna.lnk"
    assert start_menu.parent.name == "Programs"
