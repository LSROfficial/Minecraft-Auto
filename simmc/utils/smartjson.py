
import json
from typing import Any, get_origin, get_args, Union
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from collections.abc import Mapping

# 注册表
_SERIALIZERS = {}
_DESERIALIZERS = {}

def register_type(py_type, to_json_func=None, from_json_func=None):
    """
    注册自定义类型的序列化/反序列化函数。
    示例：
        register_type(MyClass, lambda x: x.to_dict(), lambda d: MyClass.from_dict(d))
    """
    if to_json_func:
        _SERIALIZERS[py_type] = to_json_func
    if from_json_func:
        _DESERIALIZERS[py_type] = from_json_func

# 内置类型支持
register_type(Path, str, lambda s: Path(s))
register_type(datetime, lambda dt: dt.isoformat(), lambda s: datetime.fromisoformat(s))
register_type(date, lambda d: d.isoformat(), lambda s: date.fromisoformat(s))
register_type(Decimal, str, Decimal)
register_type(UUID, str, UUID)
register_type(set, list, set)
register_type(tuple, list, tuple)

def _is_optional_type(tp):
    """判断是否为 Optional[T]"""
    origin = get_origin(tp)
    if origin is Union:
        args = get_args(tp)
        return len(args) == 2 and type(None) in args
    return False

def _get_non_optional_type(tp):
    """从 Optional[T] 提取 T"""
    if _is_optional_type(tp):
        args = get_args(tp)
        return args[0] if args[1] is type(None) else args[1]
    return tp

def serialize_value(value: Any, target_type: Any = None) -> Any:
    """将 Python 值递归转为 JSON 兼容对象"""
    if value is None:
        return None

    # 尝试注册类型
    value_type = type(value)
    if value_type in _SERIALIZERS:
        return _SERIALIZERS[value_type](value)

    # 推断目标类型（用于容器）
    actual_type = target_type or value_type

    # 处理泛型容器
    origin = get_origin(actual_type)
    if origin in (list, tuple, set):
        item_type = get_args(actual_type)[0] if get_args(actual_type) else Any
        return [serialize_value(item, item_type) for item in value]
    elif origin is dict or (origin is None and isinstance(value, Mapping)):
        key_type, val_type = (get_args(actual_type) + (Any, Any))[:2]
        return {
            serialize_value(k, key_type): serialize_value(v, val_type)
            for k, v in value.items()
        }
    elif origin is None and hasattr(value, '__dict__') and not isinstance(value, type):
        # 自定义类：转为 dict
        return serialize_value(value.__dict__, dict)

    # 基础类型
    if isinstance(value, (str, int, float, bool)):
        return value

    raise TypeError(f"Cannot serialize {value!r} of type {value_type} (target: {actual_type})")

def deserialize_value(json_val: Any, target_type: Any) -> Any:
    """根据目标类型，将 JSON 值递归转为 Python 对象"""
    if json_val is None:
        if _is_optional_type(target_type):
            return None
        raise ValueError(f"Non-optional field requires non-null value, got null for type {target_type}")

    # 处理 Optional[T]
    main_type = _get_non_optional_type(target_type)

    # 注册类型优先
    if main_type in _DESERIALIZERS:
        return _DESERIALIZERS[main_type](json_val)

    # 泛型容器
    origin = get_origin(main_type)
    if origin in (list, tuple, set):
        item_type = get_args(main_type)[0] if get_args(main_type) else Any
        items = [deserialize_value(item, item_type) for item in json_val]
        if origin is tuple:
            return tuple(items)
        elif origin is set:
            return set(items)
        else:
            return items
    elif origin is dict or main_type is dict:
        key_type, val_type = (get_args(main_type) + (Any, Any))[:2]
        if not isinstance(json_val, dict):
            raise ValueError(f"Expected dict, got {type(json_val)} for {main_type}")
        return {
            deserialize_value(k, key_type): deserialize_value(v, val_type)
            for k, v in json_val.items()
        }

    # 基础类型
    if main_type in (str, int, float, bool):
        if type(json_val) is main_type:
            return json_val
        return main_type(json_val)

    # 自定义类：尝试用 dict 初始化
    if isinstance(main_type, type) and not isinstance(json_val, main_type):
        if isinstance(json_val, dict):
            return main_type(**json_val)
        else:
            raise ValueError(f"Cannot construct {main_type} from non-dict value: {json_val}")

    # 已是目标类型
    return json_val

# 方便的顶层函数
def dumps(obj: Any, type_hint: Any = None, **kwargs) -> str:
    serialized = serialize_value(obj, type_hint)
    return json.dumps(serialized, **kwargs)

def loads(json_str: str, target_type: Any) -> Any:
    data = json.loads(json_str)
    return deserialize_value(data, target_type)