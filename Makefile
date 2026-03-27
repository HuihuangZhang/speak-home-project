.PHONY: test test-unit test-integration test-e2e test-e2e-ui

test: test-unit test-integration

test-unit:
	cd backend && pytest tests/unit -v --cov=api --cov=agent --cov=shared --cov-report=term-missing

test-integration:
	cd backend && pytest tests/integration -v --cov=api --cov=agent --cov=shared --cov-report=term-missing

test-e2e:
	cd e2e && npx playwright test --reporter=html

test-e2e-ui:
	cd e2e && npx playwright test --ui
