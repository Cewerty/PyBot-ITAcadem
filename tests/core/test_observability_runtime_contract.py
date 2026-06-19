from pathlib import Path


def test_loki_config_enforces_14_day_retention_with_conservative_compactor_defaults() -> None:
    project_root = Path(__file__).resolve().parents[2]
    loki_config = (project_root / "observability" / "loki" / "local-config.yaml").read_text(encoding="utf-8")

    assert "limits_config:" in loki_config
    assert "retention_period: 336h" in loki_config
    assert "max_query_lookback: 336h" in loki_config
    assert "compactor:" in loki_config
    assert "working_directory: /loki/compactor" in loki_config
    assert "compaction_interval: 10m" in loki_config
    assert "retention_enabled: true" in loki_config
    assert "retention_delete_delay: 2h" in loki_config
    assert "retention_delete_worker_count: 10" in loki_config
    assert "delete_request_store: filesystem" in loki_config


def test_ci_workflow_verifies_loki_config_with_pinned_runtime_image() -> None:
    project_root = Path(__file__).resolve().parents[2]
    ci_workflow = (project_root / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")

    assert "Verify Loki production config with pinned image" in ci_workflow
    assert "grafana/loki:3.5.0" in ci_workflow
    assert "observability/loki/local-config.yaml:/etc/loki/config.yaml:ro" in ci_workflow
    assert "-config.file=/etc/loki/config.yaml" in ci_workflow
    assert "-verify-config=true" in ci_workflow


def test_observability_nginx_re_resolves_compose_service_dns_for_health_and_grafana() -> None:
    project_root = Path(__file__).resolve().parents[2]
    nginx_config = (project_root / "observability" / "nginx" / "nginx.conf").read_text(encoding="utf-8")

    assert "resolver 127.0.0.11 ipv6=off valid=30s;" in nginx_config
    assert "set $health_upstream health:8001;" in nginx_config
    assert "rewrite ^/health/(.*)$ /$1 break;" in nginx_config
    assert "proxy_pass http://$health_upstream;" in nginx_config
    assert "set $grafana_upstream grafana:3000;" in nginx_config
    assert "proxy_pass http://$grafana_upstream;" in nginx_config
