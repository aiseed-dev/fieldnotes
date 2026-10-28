"""The contributor model is used only after the farmer agreed."""

from fieldnotes import cli, llm


def test_spark_model_follows_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    assert llm.training_consent() is None
    assert llm.Backend.spark().model == llm.SPARK          # not asked yet: standard
    llm.set_training_consent(True)
    assert llm.Backend.spark().model == llm.SPARK_CONTRIBUTOR
    llm.set_training_consent(False)
    assert llm.Backend.spark().model == llm.SPARK


def test_consent_keeps_other_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "fieldnotes").mkdir()
    (tmp_path / "fieldnotes" / "settings.json").write_text('{"other": 1}')
    llm.set_training_consent(True)
    assert '"other": 1' in (tmp_path / "fieldnotes" / "settings.json").read_text()


def test_cli_consent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert cli.main(["consent"]) == 0
    assert "まだ決めていません" in capsys.readouterr().out
    assert cli.main(["consent", "yes"]) == 0
    out = capsys.readouterr().out
    assert "同意しています" in out and llm.SPARK_CONTRIBUTOR in out


def test_readings_are_asked_in_the_farmers_language(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert llm.language_setting() == llm.AUTO
    assert "in Japanese" in llm.in_language("SYS")          # auto: this machine's locale
    token = llm.device_language.set("en")                    # the phone's own language wins
    try:
        assert "in English" in llm.in_language("SYS")
    finally:
        llm.device_language.reset(token)
    llm.set_language("fr-FR")                                # a fixed language for every device
    assert llm.language_setting() == "fr" and "in French" in llm.in_language("SYS")
    llm.set_language("sw")                                   # not in the list: named by its code
    assert "'sw'" in llm.in_language("SYS")
    llm.set_language("auto")
    assert llm.language_setting() == llm.AUTO


def test_language_codes():
    assert llm.language_code("ja_JP.UTF-8") == "ja"
    assert llm.language_code("en-US") == "en"
    assert llm.language_code("Japanese_Japan") == "ja"      # Windows locale names
    assert llm.language_code("C.UTF-8") is None and llm.language_code("und") is None


def test_cli_language(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert cli.main(["language"]) == 0
    assert "自動" in capsys.readouterr().out
    assert cli.main(["language", "en"]) == 0
    assert "English (on every device)" in capsys.readouterr().out  # the CLI now speaks English too


def test_reader_setting_picks_the_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    assert llm.reader() == "spark" and llm.Backend.default().base_url == "https://api.meta.ai/v1"
    llm.set_training_consent(True)
    llm.set_reader("glimmer", url="http://10.0.0.9:11434/v1/", model="g")
    b = llm.Backend.default()
    assert (b.base_url, b.model, b.name) == ("http://10.0.0.9:11434/v1", "g", "g@10.0.0.9")
    assert llm.training_consent() is True                   # other settings kept
    llm.set_reader("spark")
    assert llm.Backend.default().model == llm.SPARK_CONTRIBUTOR
    assert llm.glimmer_url() == "http://10.0.0.9:11434/v1"  # remembered for next time


def test_cli_reader(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("MODEL_API_KEY", raising=False)     # showing the setting needs no key
    assert cli.main(["reader"]) == 0
    assert "Muse Spark" in capsys.readouterr().out
    assert cli.main(["reader", "glimmer"]) == 0
    out = capsys.readouterr().out
    assert llm.GLIMMER_URL in out and llm.GLIMMER_MODEL in out
    monkeypatch.setattr(llm, "reachable", lambda b, timeout=5: (_ for _ in ()).throw(ConnectionError()))
    assert cli.main(["reader", "--check"]) == 1
    assert "つながりません" in capsys.readouterr().out
