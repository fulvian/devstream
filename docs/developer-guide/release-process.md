# Release Process

**Target Audience**: Maintainers, release managers
**Level**: Advanced
**Type**: Reference + Procedures

## Versioning Strategy

DevStream follows **Semantic Versioning 2.0.0** (https://semver.org/):

```
MAJOR.MINOR.PATCH

MAJOR: Incompatible API changes (breaking changes)
MINOR: Backwards-compatible functionality additions
PATCH: Backwards-compatible bug fixes
```

### Version Examples

| Version | Type | Example Changes |
|---------|------|----------------|
| **1.0.0 → 2.0.0** | MAJOR | Breaking: Database schema migration required, MCP protocol change |
| **1.2.0 → 1.3.0** | MINOR | Feature: New agent delegation system, new MCP tools |
| **1.2.3 → 1.2.4** | PATCH | Fix: Memory leak in hook execution, query optimization |

### Pre-Release Versions

```
1.3.0-alpha.1    # Alpha: Internal testing, unstable
1.3.0-beta.1     # Beta: Public testing, feature-complete
1.3.0-rc.1       # Release Candidate: Production-ready candidate
```

## Release Branches

### Branch Strategy

```
main               # Production releases (protected)
  └── develop      # Development branch (default)
      ├── feature/* # Feature branches
      ├── fix/*     # Bug fix branches
      └── release/* # Release preparation branches
```

### Branch Protection Rules

**main branch**:
- ✅ Require pull request reviews (2 approvals)
- ✅ Require status checks to pass (tests, linting)
- ✅ Require branches to be up to date
- ✅ Restrict force push
- ✅ Require signed commits

**develop branch**:
- ✅ Require pull request reviews (1 approval)
- ✅ Require status checks to pass
- ✅ Allow squash merge

## Release Workflow

### Phase 1: Release Planning

**Duration**: 1 week before release

**Checklist**:
- [ ] Review roadmap and milestone
- [ ] Identify features for release
- [ ] Identify breaking changes
- [ ] Create release tracking issue
- [ ] Notify contributors of feature freeze date
- [ ] Review and update CLAUDE.md if rules changed

**GitHub Issue Template**:
```markdown
## Release Tracking: v1.3.0

**Target Date**: 2025-11-01
**Type**: Minor Release (New Features)

### Features
- [ ] #123 Agent Auto-Delegation System
- [ ] #145 Context7 Multi-Model Support
- [ ] #167 Memory Compression

### Bug Fixes
- [ ] #201 Hook execution timeout
- [ ] #215 Embedding generation failure handling

### Breaking Changes
- None

### Migration Guide Required
- No

### Documentation Updates
- [ ] Update architecture.md
- [ ] Add agent delegation guide
- [ ] Update CLAUDE.md rules

**Feature Freeze**: 2025-10-25
**Code Freeze**: 2025-10-28
**Release Date**: 2025-11-01
```

### Phase 2: Feature Freeze

**Duration**: 3 days before release

**Actions**:
1. **Create release branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/1.3.0
   git push origin release/1.3.0
   ```

2. **Update version numbers**:
   ```bash
   # Python package
   echo "1.3.0" > VERSION

   # MCP server package.json
   cd mcp-devstream-server
   npm version 1.3.0 --no-git-tag-version

   # Database schema
   sqlite3 data/devstream.db "INSERT INTO schema_version (version, description) VALUES ('1.3.0', 'Release 1.3.0')"
   ```

3. **Update CHANGELOG.md**:
   ```markdown
   ## [1.3.0] - 2025-11-01

   ### Added
   - Agent Auto-Delegation System with pattern matching and confidence scoring
   - Context7 multi-model support (GPT-4, Claude, Gemini)
   - Memory compression for large knowledge bases (>100K vectors)

   ### Changed
   - Improved hybrid search RRF algorithm (95%+ relevance rate)
   - Optimized embedding generation (300ms → 150ms average)

   ### Fixed
   - Hook execution timeout in large projects (#201)
   - Embedding generation failure handling (#215)
   - Memory leak in MCP server (#230)

   ### Deprecated
   - Legacy task creation API (use MCP tools instead)

   ### Security
   - Updated dependencies to patch CVE-2025-12345

   ### Migration Guide
   - No breaking changes, automatic migration
   ```

4. **Run pre-release tests**:
   ```bash
   # Run full test suite
   ./scripts/run-all-tests.sh

   # Run smoke tests
   ./scripts/smoke-test.sh

   # Run performance benchmarks
   ./scripts/benchmark.sh

   # Check for regressions
   ./scripts/regression-test.sh
   ```

### Phase 3: Code Freeze

**Duration**: 2 days before release

**Actions**:
1. **Freeze all changes** (only critical bug fixes allowed)
2. **Final testing**:
   - [ ] Unit tests: 100% pass rate
   - [ ] Integration tests: 100% pass rate
   - [ ] E2E tests: 100% pass rate
   - [ ] Performance benchmarks: No regressions
   - [ ] Manual smoke testing

3. **Documentation review**:
   - [ ] CHANGELOG.md accurate and complete
   - [ ] README.md updated
   - [ ] CLAUDE.md updated if rules changed
   - [ ] API documentation generated
   - [ ] Migration guide written (if breaking changes)

4. **Security audit**:
   - [ ] Dependency vulnerability scan
   - [ ] Code security scan
   - [ ] Secrets scan (no hardcoded credentials)

### Phase 4: Release Candidate

**Duration**: 1 day before release

**Actions**:
1. **Create release candidate tag**:
   ```bash
   git checkout release/1.3.0
   git tag -a v1.3.0-rc.1 -m "Release Candidate 1.3.0-rc.1"
   git push origin v1.3.0-rc.1
   ```

2. **Deploy to staging environment**:
   ```bash
   ./scripts/deploy-staging.sh v1.3.0-rc.1
   ```

3. **Run final validation**:
   - [ ] Staging deployment successful
   - [ ] All smoke tests pass in staging
   - [ ] Manual testing by 2+ contributors
   - [ ] Performance validation in staging

4. **Create GitHub Pre-Release**:
   - Go to https://github.com/yourusername/devstream/releases/new
   - Tag: `v1.3.0-rc.1`
   - Title: `DevStream 1.3.0 RC1`
   - Description: Changelog + "This is a release candidate. Please test and report issues."
   - Check "This is a pre-release"
   - Publish release

### Phase 5: Production Release

**Release Day**

**Actions**:
1. **Merge release branch to main**:
   ```bash
   # Create pull request: release/1.3.0 → main
   gh pr create \
     --base main \
     --head release/1.3.0 \
     --title "Release v1.3.0" \
     --body "$(cat CHANGELOG.md | sed -n '/## \[1.3.0\]/,/## \[/p' | head -n -1)"

   # Wait for approvals and CI checks
   # Merge pull request
   gh pr merge --merge --delete-branch
   ```

2. **Create release tag**:
   ```bash
   git checkout main
   git pull origin main
   git tag -a v1.3.0 -m "Release 1.3.0"
   git push origin v1.3.0
   ```

3. **Create GitHub Release**:
   - Go to https://github.com/yourusername/devstream/releases/new
   - Tag: `v1.3.0`
   - Title: `DevStream 1.3.0 - [Release Name]`
   - Description: Full changelog from CHANGELOG.md
   - Attach artifacts:
     - `devstream-1.3.0.tar.gz` (source archive)
     - `mcp-devstream-server-1.3.0.tgz` (MCP server package)
   - Publish release

4. **Deploy to production**:
   ```bash
   ./scripts/deploy-production.sh v1.3.0
   ```

5. **Verify production deployment**:
   - [ ] Production smoke tests pass
   - [ ] Health checks pass
   - [ ] Monitoring alerts clean
   - [ ] User-facing features working

6. **Merge main back to develop**:
   ```bash
   git checkout develop
   git merge main
   git push origin develop
   ```

7. **Announce release**:
   - [ ] Post to GitHub Discussions
   - [ ] Update documentation website
   - [ ] Notify users via email/Slack
   - [ ] Post to social media (if applicable)

### Phase 6: Post-Release

**Actions within 24 hours**:
1. **Monitor production**:
   - [ ] Check error logs
   - [ ] Monitor performance metrics
   - [ ] Review user feedback
   - [ ] Address critical issues immediately

2. **Update project boards**:
   - [ ] Close release milestone
   - [ ] Create next milestone
   - [ ] Update roadmap

3. **Retrospective** (within 1 week):
   - What went well?
   - What could be improved?
   - Action items for next release

## Hotfix Process

### When to Create Hotfix

**Criteria for hotfix**:
- ✅ Critical bug affecting production users
- ✅ Security vulnerability
- ✅ Data corruption issue
- ✅ Service outage

**Not requiring hotfix** (wait for next release):
- ❌ Minor bugs
- ❌ Feature requests
- ❌ Performance optimizations (non-critical)

### Hotfix Workflow

**Duration**: Same day (urgent) to 2 days (critical)

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/1.2.5
git push origin hotfix/1.2.5

# 2. Fix the issue
# ... make changes ...
git add .
git commit -m "fix: critical issue description"

# 3. Update version and changelog
echo "1.2.5" > VERSION
# Update CHANGELOG.md with hotfix entry

# 4. Test thoroughly
./scripts/run-all-tests.sh
./scripts/smoke-test.sh

# 5. Create PR to main
gh pr create \
  --base main \
  --head hotfix/1.2.5 \
  --title "Hotfix v1.2.5: [Issue Description]" \
  --body "## Hotfix\n\n**Issue**: [Description]\n**Fix**: [Description]\n\n**Testing**: All tests pass"

# 6. Merge and tag
gh pr merge --merge
git checkout main
git pull origin main
git tag -a v1.2.5 -m "Hotfix 1.2.5"
git push origin v1.2.5

# 7. Deploy to production immediately
./scripts/deploy-production.sh v1.2.5

# 8. Merge back to develop
git checkout develop
git merge main
git push origin develop

# 9. Create GitHub Release
gh release create v1.2.5 \
  --title "DevStream 1.2.5 (Hotfix)" \
  --notes "## Hotfix 1.2.5\n\n**Critical Fix**: [Description]"
```

## Changelog Maintenance

### Format

**File**: `CHANGELOG.md`

```markdown
# Changelog

All notable changes to DevStream are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Feature in development (not yet released)

### Changed
- Improvement in development

## [1.3.0] - 2025-11-01

### Added
- Agent Auto-Delegation System with pattern matching (#123)
- Context7 multi-model support (#145)
- Memory compression for large knowledge bases (#167)

### Changed
- Improved hybrid search RRF algorithm (95%+ relevance rate)
- Optimized embedding generation (300ms → 150ms average)

### Fixed
- Hook execution timeout in large projects (#201)
- Embedding generation failure handling (#215)

### Security
- Updated dependencies to patch CVE-2025-12345

## [1.2.4] - 2025-10-15

### Fixed
- Memory leak in MCP server (#230)
- Database connection pooling issue (#240)

## [1.2.3] - 2025-10-01

...
```

### Changelog Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Added** | New features | Agent delegation, new MCP tools |
| **Changed** | Changes to existing functionality | API improvements, performance |
| **Deprecated** | Soon-to-be-removed features | Legacy APIs |
| **Removed** | Removed features | Deprecated APIs removed |
| **Fixed** | Bug fixes | Memory leak, timeout issue |
| **Security** | Security fixes | Vulnerability patches |

## Migration Guides

### When to Write Migration Guide

**Required for**:
- ✅ Breaking changes (MAJOR version bump)
- ✅ Database schema changes
- ✅ Configuration format changes
- ✅ API changes requiring code updates

**Example Migration Guide**:

**File**: `docs/migration/v2.0.0.md`

```markdown
# Migration Guide: v1.x → v2.0.0

**Breaking Changes**: Yes
**Migration Time**: ~15 minutes
**Rollback**: Backup required

## Breaking Changes

### 1. Database Schema Migration

**Change**: semantic_memory table structure updated

**Action Required**:
```bash
# Backup database
cp data/devstream.db data/devstream.db.backup

# Run migration script
.devstream/bin/python scripts/migrate-v2.py

# Verify migration
sqlite3 data/devstream.db "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1;"
# Expected output: 2.0.0
```

**Rollback**:
```bash
# Restore backup
mv data/devstream.db.backup data/devstream.db
```

### 2. Configuration Format Change

**Change**: `.env.devstream` format updated

**Old Format**:
```bash
DEVSTREAM_MEMORY_ENABLED=1
DEVSTREAM_CONTEXT7_ENABLED=1
```

**New Format**:
```bash
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_CONTEXT7_ENABLED=true
```

**Action Required**:
```bash
# Auto-migrate configuration
.devstream/bin/python scripts/migrate-config.py

# Manual migration
sed -i '' 's/=1$/=true/g' .env.devstream
sed -i '' 's/=0$/=false/g' .env.devstream
```

### 3. MCP Tool Name Changes

**Change**: Tool names standardized

| Old Name | New Name |
|----------|----------|
| `list_tasks` | `devstream_list_tasks` |
| `store_memory` | `devstream_store_memory` |

**Action Required**:
- Update custom scripts using MCP tools
- No action required for hook system (auto-updated)

## Post-Migration Validation

```bash
# Run smoke tests
./scripts/smoke-test.sh

# Expected output:
# ✅ Database schema version: 2.0.0
# ✅ Configuration format valid
# ✅ MCP tools accessible
# ✅ All tests pass
```

## Support

If you encounter issues during migration:
- Check migration logs: `~/.claude/logs/devstream/migration.log`
- Create issue: https://github.com/yourusername/devstream/issues
- Join Slack: #devstream-support
```

## Rollback Procedures

### When to Rollback

**Criteria**:
- ✅ Critical bug discovered in production
- ✅ Performance degradation > 50%
- ✅ Data corruption detected
- ✅ Service outage

### Rollback Steps

```bash
# 1. Identify last known good version
git tag --sort=-version:refname | head -5

# 2. Deploy previous version
./scripts/deploy-production.sh v1.2.4

# 3. Verify rollback successful
./scripts/smoke-test.sh

# 4. Restore database backup (if schema changed)
# WARNING: Data loss possible - evaluate carefully
cp data/devstream.db.backup data/devstream.db

# 5. Notify users
echo "⚠️  Rolled back to v1.2.4 due to critical issue. Investigating."

# 6. Document incident
# Create post-mortem document in docs/incidents/
```

## Release Checklist

### Pre-Release Checklist

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code coverage ≥ 95% for new code
- [ ] No mypy errors (`mypy --strict`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers updated
- [ ] Migration guide written (if breaking changes)
- [ ] Security audit completed
- [ ] Performance benchmarks show no regressions
- [ ] Release notes drafted
- [ ] Approvals obtained (2+ maintainers)

### Release Day Checklist

- [ ] Release branch merged to main
- [ ] Release tag created
- [ ] GitHub Release published
- [ ] Production deployment successful
- [ ] Smoke tests pass in production
- [ ] Monitoring alerts clean
- [ ] Documentation website updated
- [ ] Release announcement posted
- [ ] main merged back to develop

### Post-Release Checklist

- [ ] Production monitoring active
- [ ] Error logs reviewed (first 24 hours)
- [ ] User feedback collected
- [ ] Critical issues addressed
- [ ] Release milestone closed
- [ ] Next milestone created
- [ ] Retrospective scheduled

## Tools and Scripts

### Release Scripts

**File**: `scripts/release.sh`

```bash
#!/bin/bash
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    exit 1
fi

echo "🚀 Starting release process for v$VERSION"

# Verify on release branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ ! $BRANCH =~ ^release/ ]]; then
    echo "❌ Must be on release branch"
    exit 1
fi

# Run tests
echo "🧪 Running tests..."
./scripts/run-all-tests.sh

# Update version
echo "📝 Updating version..."
echo "$VERSION" > VERSION
cd mcp-devstream-server && npm version "$VERSION" --no-git-tag-version && cd ..

# Update changelog
echo "📄 Update CHANGELOG.md manually, then press Enter to continue..."
read

# Commit version bump
git add VERSION mcp-devstream-server/package.json CHANGELOG.md
git commit -m "chore: bump version to $VERSION"
git push origin "$BRANCH"

# Create PR
echo "📬 Creating pull request to main..."
gh pr create \
    --base main \
    --head "$BRANCH" \
    --title "Release v$VERSION" \
    --body "$(cat CHANGELOG.md | sed -n "/## \[$VERSION\]/,/## \[/p" | head -n -1)"

echo "✅ Release process initiated. Review PR and merge to complete release."
```

### Version Bump Script

**File**: `scripts/bump-version.sh`

```bash
#!/bin/bash
set -e

TYPE=$1  # major, minor, or patch

if [ -z "$TYPE" ]; then
    echo "Usage: ./scripts/bump-version.sh <major|minor|patch>"
    exit 1
fi

CURRENT_VERSION=$(cat VERSION)
echo "Current version: $CURRENT_VERSION"

# Parse version
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Bump version
case $TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "❌ Invalid type: $TYPE"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Confirm
read -p "Proceed with version bump? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Update version
echo "$NEW_VERSION" > VERSION
cd mcp-devstream-server && npm version "$NEW_VERSION" --no-git-tag-version && cd ..

echo "✅ Version bumped to $NEW_VERSION"
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-01
**Release Manager**: DevStream Team
