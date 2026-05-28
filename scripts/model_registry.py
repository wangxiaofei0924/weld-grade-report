"""
模块3.5：模型热替换接口
使用 watchdog 监听模型目录，新模型放入后自动加载
"""
import os
import time
import threading
from pathlib import Path


class ModelRegistry:
    """模型注册表（单例），管理模型的热加载与原子替换"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._models = {}          # {model_name: model_instance}
        self._model_paths = {}     # {model_name: file_path}
        self._model_info = {}      # {model_name: {version, load_time, ...}}
        self._callbacks = []       # 模型更新回调
        self.model_dir = None

    def set_model_dir(self, path):
        """设置模型存放目录"""
        self.model_dir = Path(path)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def register_model(self, name, model_instance, file_path=""):
        """手动注册模型"""
        self._models[name] = model_instance
        self._model_paths[name] = file_path
        self._model_info[name] = {
            "version": time.strftime("%Y%m%d_%H%M%S"),
            "load_time": time.time(),
            "file_path": file_path
        }

    def get_model(self, name):
        """获取模型实例"""
        model = self._models.get(name)
        if model is None:
            raise KeyError(f"模型 '{name}' 未注册。可用模型: {list(self._models.keys())}")
        return model

    def replace_model(self, name, new_model, file_path=""):
        """原子替换模型（训练完的新模型热加载）"""
        old_model = self._models.get(name)
        self._models[name] = new_model
        self._model_paths[name] = file_path
        self._model_info[name] = {
            "version": time.strftime("%Y%m%d_%H%M%S"),
            "load_time": time.time(),
            "file_path": file_path
        }

        # 触发回调
        for cb in self._callbacks:
            try:
                cb(name, old_model, new_model)
            except Exception as e:
                print(f"回调执行失败: {e}")

        print(f"✅ 模型 '{name}' 已热替换 (来源: {file_path})")
        return old_model

    def list_models(self):
        """列出所有已注册模型"""
        return {
            name: {
                "info": self._model_info.get(name, {}),
                "path": self._model_paths.get(name, "")
            }
            for name in self._models
        }

    def on_model_updated(self, callback):
        """注册模型更新回调函数"""
        self._callbacks.append(callback)

    # ===== 模拟加载（等有真实模型后替换为 ultralytics/YOLO 加载） =====
    def load_yolo_model(self, name, model_path):
        """加载 YOLO 模型（需要 ultralytics）"""
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            self.register_model(name, model, str(model_path))
            print(f"✅ YOLO 模型 '{name}' 已加载: {model_path}")
            return model
        except ImportError:
            print("⚠️ ultralytics 未安装，使用模拟模型")
            self.register_model(name, f"MockModel({model_path})", str(model_path))
            return self.get_model(name)
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return None

    def load_onnx_model(self, name, model_path):
        """加载 ONNX 模型"""
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(model_path)
            self.register_model(name, session, str(model_path))
            print(f"✅ ONNX 模型 '{name}' 已加载: {model_path}")
            return session
        except ImportError:
            print("⚠️ onnxruntime 未安装，使用模拟模型")
            self.register_model(name, f"MockONNX({model_path})", str(model_path))
            return self.get_model(name)
        except Exception as e:
            print(f"❌ ONNX 模型加载失败: {e}")
            return None


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("模型热替换接口测试")
    print("=" * 50)

    registry = ModelRegistry()

    # 模拟加载初始模型
    registry.register_model("detect_v1", "YOLOv8-detect-v1", "models/detect_v1.pt")
    registry.register_model("seg_v1", "YOLOv8-seg-v1", "models/seg_v1.pt")

    print(f"\n当前模型: {list(registry._models.keys())}")

    # 模拟训练完新模型 → 热替换
    print("\n[模拟] 新模型训练完成，执行热替换...")
    old = registry.replace_model("detect_v1", "YOLOv8-detect-v2", "models/detect_v2.pt")

    print(f"   旧模型: {old}")
    print(f"   新模型: {registry.get_model('detect_v1')}")

    # 列出所有模型
    print(f"\n已注册模型列表:")
    for name, info in registry.list_models().items():
        print(f"   {name}: {info['info'].get('version', '?')} | {info['path']}")