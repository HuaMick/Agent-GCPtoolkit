#!/bin/bash
set -e

echo "=== Agent-GCPtoolkit Integration Tests ==="

PROJECT_ROOT="/home/code/myagents/Agent-GCPtoolkit"
cd "$PROJECT_ROOT"

echo ""
echo "1. Testing clean..."
./scripts/clean.sh
[ ! -f build-artifacts/dist/*.whl ] && echo "✓ Clean successful" || (echo "✗ Clean failed" && exit 1)

echo ""
echo "2. Testing build..."
./scripts/build.sh
[ -f build-artifacts/dist/agent_gcptoolkit-*.whl ] && echo "✓ Build successful" || (echo "✗ Build failed" && exit 1)

echo ""
echo "3. Testing UV tool install installation..."
./scripts/install-global.sh
which gcptoolkit && echo "✓ CLI accessible globally" || (echo "✗ CLI not in PATH" && exit 1)
gcptoolkit version && echo "✓ CLI works" || (echo "✗ CLI command failed" && exit 1)

echo ""
echo "4. Testing imports..."
python3 -c "from agent_gcptoolkit.secrets import get_secret" && echo "✓ Old import works" || (echo "✗ Old import failed" && exit 1)
python3 -c "from backend.services.secrets.src.workflows.secret_operations import get_secret" && echo "✓ New import works" || (echo "✗ New import failed" && exit 1)

echo ""
echo "5. Testing CLI commands..."
gcptoolkit version | grep "0.1.0" && echo "✓ Version command works" || (echo "✗ Version command failed" && exit 1)
gcptoolkit --help | grep "Available commands" && echo "✓ Help command works" || (echo "✗ Help command failed" && exit 1)

echo ""
echo "6. Testing exit codes..."
export TEST_SECRET="value123"
gcptoolkit secrets get TEST_SECRET --quiet > /dev/null
[ $? -eq 0 ] && echo "✓ Exit code 0 on success" || (echo "✗ Exit code wrong on success" && exit 1)

gcptoolkit secrets get NONEXISTENT_SECRET_XYZ --quiet > /dev/null 2>&1
[ $? -eq 1 ] && echo "✓ Exit code 1 on runtime error" || (echo "✗ Exit code wrong on runtime error" && exit 1)

gcptoolkit secrets get > /dev/null 2>&1
[ $? -eq 2 ] && echo "✓ Exit code 2 on usage error" || (echo "✗ Exit code wrong on usage error" && exit 1)

echo ""
echo "7. Testing quiet mode..."
OUTPUT=$(gcptoolkit secrets get TEST_SECRET --quiet 2>&1)
[ "$OUTPUT" = "value123" ] && echo "✓ Quiet mode outputs only value" || (echo "✗ Quiet mode output wrong: $OUTPUT" && exit 1)

echo ""
echo "8. Testing secret name validation..."
gcptoolkit secrets get "api.key" > /dev/null 2>&1
[ $? -eq 2 ] && echo "✓ Rejects invalid secret name (dots)" || (echo "✗ Should reject dots in secret name" && exit 1)

gcptoolkit secrets get "MY_VALID_SECRET-123" --quiet > /dev/null 2>&1
[ $? -eq 0 ] || [ $? -eq 1 ] && echo "✓ Accepts valid secret name" || (echo "✗ Should accept valid secret name" && exit 1)

echo ""
echo "9. Testing GCP_PROJECT env var..."
# This test requires actual GCP access, so we just verify the env var is read
export GCP_PROJECT="test-project-id"
python3 -c "
from backend.services.secrets.src.domains.gcp_client import GCPSecretClient
client = GCPSecretClient()
project_id = client.get_project_id()
assert project_id == 'test-project-id', f'Expected test-project-id, got {project_id}'
print('✓ GCP_PROJECT env var is read correctly')
"

echo ""
echo "10. Testing backward compatibility..."
python3 -c "
import warnings
warnings.simplefilter('always', DeprecationWarning)
with warnings.catch_warnings(record=True) as w:
    from agent_gcptoolkit.secrets import get_secret
    assert len(w) == 0, 'No warning on import'
    # Calling the function should trigger warning
    try:
        get_secret('TEST_SECRET')
    except:
        pass  # Expected to fail without GCP
    assert any('deprecated' in str(warning.message).lower() for warning in w), 'Deprecation warning shown'
print('✓ Deprecation warning works')
"

echo ""
echo "11. Testing package structure..."
[ -d "$PROJECT_ROOT/backend/services/secrets/src/domains" ] && echo "✓ Backend structure exists" || (echo "✗ Backend structure missing" && exit 1)
[ -d "$PROJECT_ROOT/backend/services/secrets/src/workflows" ] && echo "✓ Workflows structure exists" || (echo "✗ Workflows structure missing" && exit 1)
[ -d "$PROJECT_ROOT/frontend/cli" ] && echo "✓ Frontend structure exists" || (echo "✗ Frontend structure missing" && exit 1)

echo ""
echo "12. Testing help completeness..."
gcptoolkit version --help | grep -q "Show version" && echo "✓ version --help has description" || (echo "✗ version --help incomplete" && exit 1)
gcptoolkit update --help | grep -q "build-artifacts" && echo "✓ update --help has description" || (echo "✗ update --help incomplete" && exit 1)
gcptoolkit secrets get --help | grep -q "Fetch a secret" && echo "✓ secrets get --help has description" || (echo "✗ secrets get --help incomplete" && exit 1)

echo ""
echo "=== All integration tests passed ==="
echo ""
echo "Summary of improvements verified:"
echo "  ✓ UV tool install (CLI globally accessible)"
echo "  ✓ GCP_PROJECT env var support"
echo "  ✓ Exit codes (0/1/2) standardized"
echo "  ✓ Quiet mode suppresses stderr"
echo "  ✓ Help completeness for all commands"
echo "  ✓ Secret name validation"
