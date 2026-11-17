import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        """功能：为每个测试加载独立的标准库配置初始化模块。

        输入：self：当前 unittest 测试实例。
        输出：None；将模块保存为 self.module，不触碰项目真实 .env。
        """
        spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts/bootstrap.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_generates_unique_config_without_overwriting_existing(self):
        """功能：验证不同安装生成独立配置，重复初始化保留已有文件。

        输入：self：测试实例；内部创建含中文/空格的临时目录与公开模板。
        输出：None；断言配置生成、幂等与项目隔离成立，失败抛出断言异常。
        """
        with tempfile.TemporaryDirectory(prefix="售后 demo ") as temp:
            root = Path(temp)
            (root / ".env.example").write_text(
                (ROOT / ".env.example").read_text(), encoding="utf-8"
            )
            self.assertTrue(self.module.initialize(root))
            first = (root / ".env").read_bytes()
            self.assertNotIn(b"DEMO_API_TOKEN=\n", first)
            self.assertFalse(self.module.initialize(root))
            self.assertEqual(first, (root / ".env").read_bytes())
            with tempfile.TemporaryDirectory() as other:
                other_root = Path(other)
                (other_root / ".env.example").write_text((ROOT / ".env.example").read_text())
                self.module.initialize(other_root)
                self.assertNotEqual(first, (other_root / ".env").read_bytes())
                self.assertNotEqual(
                    self.module.read_config(root / ".env")["COMPOSE_PROJECT_NAME"],
                    self.module.read_config(other_root / ".env")["COMPOSE_PROJECT_NAME"],
                )

    def test_existing_invalid_config_is_rejected_without_overwrite(self):
        """功能：验证无效的已有配置被拒绝且字节内容保持不变。

        输入：self：测试实例；内部创建无效的临时 .env。
        输出：None；断言抛出 ValueError 且未覆盖文件。
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = "POSTGRES_PASSWORD=\nDEMO_API_TOKEN=\n"
            (root / ".env").write_text(original)
            with self.assertRaises(ValueError):
                self.module.initialize(root)
            self.assertEqual((root / ".env").read_text(), original)

    def test_existing_dollar_secret_is_rejected_without_echo(self):
        """功能：验证不安全配置被拒绝且错误消息不回显私密值。

        输入：self：测试实例；内部构造含美元符号的假凭据。
        输出：None；断言配置拒绝且异常不含假凭据。
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private = "private$dollar_value_which_must_not_be_echoed"
            (root / ".env").write_text(f"POSTGRES_PASSWORD={private}\nDEMO_API_TOKEN={private}\n")
            with self.assertRaises(ValueError) as caught:
                self.module.initialize(root)
            self.assertNotIn(private, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
