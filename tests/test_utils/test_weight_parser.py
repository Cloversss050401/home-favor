"""重量解析工具测试：'番茄 500g' / '鸡胸肉 1kg' / 纯数字 / 空串。"""
from app.common.utils import format_weight, parse_weight


class TestParseWeight:
    def test_name_with_gram(self):
        r = parse_weight("番茄 500g")
        assert r.name == "番茄"
        assert r.available_weight == 500.0

    def test_name_with_gram_no_space(self):
        r = parse_weight("番茄500克")
        assert r.name == "番茄"
        assert r.available_weight == 500.0

    def test_name_with_kg(self):
        r = parse_weight("鸡胸肉 1kg")
        assert r.name == "鸡胸肉"
        assert r.available_weight == 1000.0

    def test_name_only_returns_none_weight(self):
        r = parse_weight("鸡胸肉")
        assert r.name == "鸡胸肉"
        assert r.available_weight is None

    def test_pure_weight_returns_empty_name(self):
        r = parse_weight("500g")
        assert r.name == ""
        assert r.available_weight == 500.0

    def test_empty_string(self):
        r = parse_weight("")
        assert r.name == ""
        assert r.available_weight is None

    def test_whitespace_only(self):
        r = parse_weight("   ")
        assert r.name == ""
        assert r.available_weight is None

    def test_decimal_weight(self):
        r = parse_weight("鸡蛋 1.5kg")
        assert r.name == "鸡蛋"
        assert r.available_weight == 1500.0


class TestFormatWeight:
    def test_grams(self):
        assert format_weight(500) == "500g"

    def test_kilograms(self):
        assert format_weight(1500) == "1.50kg"

    def test_boundary(self):
        assert format_weight(1000) == "1.00kg"