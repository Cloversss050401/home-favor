"""同义词工具测试：canonical 归一 / merge_synonyms 合并计数 / 文件加载。"""
from app.common.utils import SYNONYM_FILE, canonical, has_synonym, merge_synonyms


class TestCanonical:
    def test_builtin_alias(self):
        assert canonical("西红柿") == "番茄"
        assert canonical("圣女果") == "番茄"
        assert canonical("土鸡蛋") == "鸡蛋"

    def test_file_loaded_alias(self):
        """resources/dict/synonyms.json 中新增的同义词应被加载生效。"""
        assert SYNONYM_FILE.exists(), "同义词字典文件不存在"
        assert canonical("河虾") == "虾"
        assert canonical("红富士") == "苹果"

    def test_unknown_name_unchanged(self):
        assert canonical("牛油果") == "牛油果"

    def test_empty_name(self):
        assert canonical("") == ""
        assert canonical(None) == ""

    def test_self_mapping(self):
        assert canonical("番茄") == "番茄"


class TestMergeSynonyms:
    def test_merge_counts(self):
        result = merge_synonyms(["西红柿", "番茄", "土鸡蛋", "番茄"])
        assert result == {"番茄": 3, "鸡蛋": 1}

    def test_merge_empty(self):
        assert merge_synonyms([]) == {}


class TestHasSynonym:
    def test_exists(self):
        assert has_synonym("番茄") is True
        assert has_synonym("西红柿") is True

    def test_not_exists(self):
        assert has_synonym("牛油果") is False