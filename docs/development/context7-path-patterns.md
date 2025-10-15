# Context7 Path Patterns Documentation

**Version**: 2.2.0
**Date**: 2025-10-15
**Status**: Production Ready

## Overview

This document describes the Context7-compliant path patterns implemented across DevStream scripts to replace hardcoded paths with dynamic environment-based configuration. These patterns enable DevStream to work correctly in multi-project environments while maintaining backward compatibility.

## Context7 Path Detection Pattern

### Priority Order

The Context7 pattern follows a consistent priority order for path detection:

1. **Environment Variable** - `DEVSTREAM_ROOT` (highest priority)
2. **Script Location Detection** - Two levels up from `scripts/` directory
3. **Common Installation Locations** - Standard installation paths
4. **Current Working Directory** - Fallback to current directory
5. **Error Handling** - Informative error messages with setup instructions

### Implementation Pattern

#### Shell Script Pattern

```bash
# Context7 Pattern: Get DevStream root using environment detection
get_devstream_root() {
    # Priority 1: DEVSTREAM_ROOT environment variable
    if [ -n "${DEVSTREAM_ROOT:-}" ]; then
        echo "$DEVSTREAM_ROOT"
        return 0
    fi

    # Priority 2: Script location detection (two levels up from scripts/)
    if [ -f "${BASH_SOURCE[0]%/*/*}/start-devstream.sh" ]; then
        echo "${BASH_SOURCE[0]%/*/*}"
        return 0
    fi

    # Priority 3: Common installation locations
    local possible_paths=(
        "$HOME/.devstream"
        "$HOME/devstream"
        "/opt/devstream"
        "$(pwd)"
    )

    for path in "${possible_paths[@]}"; do
        if [ -f "$path/start-devstream.sh" ]; then
            echo "$path"
            return 0
        fi
    done

    return 1
}
```

#### Python Pattern

```python
def get_devstream_root() -> Path:
    """
    Get DevStream root using Context7 patterns.

    Priority 1: DEVSTREAM_ROOT environment variable
    Priority 2: Script location detection (two levels up from scripts/)
    Priority 3: Current working directory
    Priority 4: Common installation locations

    Returns:
        Path to DevStream root directory

    Raises:
        RuntimeError: If DevStream root cannot be determined
    """
    # Priority 1: DEVSTREAM_ROOT environment variable
    devstream_root = os.getenv("DEVSTREAM_ROOT")
    if devstream_root and Path(devstream_root).exists():
        return Path(devstream_root).absolute()

    # Priority 2: Script location detection
    script_file = Path(__file__)
    if script_file.exists():
        # Two levels up from scripts/ directory
        potential_root = script_file.parent.parent
        if (potential_root / "start-devstream.sh").exists():
            return potential_root.absolute()

    # Priority 3: Current working directory
    cwd = Path.cwd()
    if (cwd / "start-devstream.sh").exists():
        return cwd.absolute()

    # Priority 4: Common installation locations
    possible_locations = [
        Path.home() / ".devstream",
        Path.home() / "devstream",
        Path("/opt/devstream"),
        Path.cwd(),
    ]

    for location in possible_locations:
        if location.exists() and (location / "start-devstream.sh").exists():
            return location.absolute()

    # If nothing found, raise an informative error
    raise RuntimeError(
        "DevStream installation not found! Please set DEVSTREAM_ROOT environment variable "
        "or ensure DevStream is properly installed with start-devstream.sh"
    )
```

## Updated Scripts

### 1. devstream-launcher.sh

**File**: `/scripts/devstream-launcher.sh`
**Lines Modified**: 19-85 (function replacement)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 23)
- `/Users/fulvioventura/devstream/scripts/install-devstream-global.sh` (line 36)

**Key Changes**:
- Added `get_devstream_root()` function with Context7 pattern
- Updated `find_devstream_installation()` to use dynamic detection
- Improved error messages with setup instructions

### 2. test-multi-project.sh

**File**: `/scripts/test-multi-project.sh`
**Lines Modified**: 20-61 (configuration replacement)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 21)
- `/Users/fulvioventura/accountabilly` (line 22 - now uses first argument or current directory)

**Key Changes**:
- Added Context7-compatible `get_devstream_root()` function
- Dynamic project path detection via command line argument
- Enhanced validation and error handling

### 3. devstream-config.py

**File**: `/scripts/devstream-config.py`
**Lines Modified**: 14-63 (new function), 174-187 (function update)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 125)

**Key Changes**:
- Added `get_devstream_root()` function with full type hints
- Updated `get_startup_command()` to use dynamic path detection
- Graceful fallback for backward compatibility

### 4. simple-launcher.sh

**File**: `/scripts/simple-launcher.sh`
**Lines Modified**: 17-57 (new function), 133-165 (main function updates)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream/scripts/devstream-init.py` (lines 93-94)
- `/Users/fulvioventura/devstream` (line 102)

**Key Changes**:
- Added Context7 path detection function
- Updated initialization and installation detection
- Improved error messages with specific path information

### 5. start-project-devstream.sh

**File**: `/scripts/start-project-devstream.sh`
**Lines Modified**: 14-49 (new function), 57-94 (usage and header updates)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 17)

**Key Changes**:
- Dynamic DevStream root detection
- Updated usage documentation to reflect auto-detection
- Enhanced validation in header function

### 6. devstream-provider.sh

**File**: `/scripts/devstream-provider.sh`
**Lines Modified**: 14-49 (new function), 81-106 (validation updates)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 17)

**Key Changes**:
- Context7-compatible path detection
- Enhanced project validation with better error handling
- Dynamic initialization script path resolution

### 7. devstream-init.py

**File**: `/scripts/devstream-init.py`
**Lines Modified**: 21-70 (new function), 469-482 (function update), 519-547 (adaptation update), 652-666 (basic CLAUDE.md update)
**Hardcoded Paths Removed**:
- `/Users/fulvioventura/devstream` (line 418)
- `/Users/fulvioventura/devstream/scripts/simple-launcher.sh` (line 475)
- `cd /Users/fulvioventura/devstream` (line 483)
- `/Users/fulvioventura/devstream/CLAUDE.md` (line 591)

**Key Changes**:
- Added comprehensive `get_devstream_root()` function
- Updated CLAUDE.md creation and adaptation to use dynamic paths
- Fixed project-specific launcher examples
- Enhanced error handling for missing DevStream installation

## Usage Examples

### Setting Custom DevStream Root

```bash
# Environment variable (highest priority)
export DEVSTREAM_ROOT=/path/to/my/devstream
./scripts/simple-launcher.sh start anthropic

# One-time usage
DEVSTREAM_ROOT=/path/to/my/devstream ./scripts/devstream-config.py get-provider

# Using with project-specific path
./scripts/start-project-devstream.sh /my/project /my/devstream
```

### Multi-Project Environments

```bash
# From any project directory
cd /path/to/project1
./scripts/simple-launcher.sh start anthropic

# Automatically detects DevStream installation
# Works across different projects without configuration

# Test multi-project setup
./scripts/test-multi-project.sh /path/to/project1
```

### Script Development

```bash
# During development with local DevStream clone
export DEVSTREAM_ROOT=$HOME/devstream-dev
./scripts/devstream-init.py /path/to/test-project

# Script automatically uses development version
```

## Environment Variables

### DEVSTREAM_ROOT

**Description**: Path to DevStream installation directory
**Priority**: 1 (highest)
**Format**: Absolute path to directory containing `start-devstream.sh`
**Example**: `export DEVSTREAM_ROOT=/opt/devstream`

### Common Installation Locations

The Context7 pattern automatically searches these locations:
1. `$HOME/.devstream`
2. `$HOME/devstream`
3. `/opt/devstream`
4. Current working directory

### Script Location Detection

Scripts automatically detect DevStream root based on their location:
- Scripts in `scripts/` directory detect root as two levels up
- Example: `/devstream/scripts/devstream-launcher.sh` → `/devstream/`

## Error Handling

### Enhanced Error Messages

All scripts now provide informative error messages:

```bash
DevStream installation not found!
Set DEVSTREAM_ROOT environment variable or ensure DevStream is properly installed

Auto-detection attempted:
  - DEVSTREAM_ROOT environment variable: [not set]
  - Script location detection: /path/to/scripts/..
  - Common locations: $HOME/.devstream, $HOME/devstream, /opt/devstream
```

### Validation

Scripts validate DevStream installation before proceeding:
- Check for `start-devstream.sh` existence
- Verify script permissions
- Validate project directory existence
- Provide clear next-step instructions

## Backward Compatibility

The Context7 patterns maintain full backward compatibility:

1. **Existing Installations**: Work without changes
2. **Environment Variables**: Optional but supported
3. **Default Behavior**: Unchanged for standard installations
4. **Error Messages**: More informative but not breaking

## Migration Guide

### For Users

No action required for existing installations. Scripts will automatically detect DevStream location.

### For Developers

When creating new scripts:

```bash
# Include this function in new shell scripts
get_devstream_root() {
    # [Copy the standard Context7 implementation]
}

# Use dynamic paths
DEVSTREAM_ROOT=$(get_devstream_root)
if [ $? -ne 0 ]; then
    echo "Error: DevStream installation not found"
    exit 1
fi
```

```python
# Include this function in new Python scripts
def get_devstream_root() -> Path:
    # [Copy the standard Context7 implementation]
    pass

# Use dynamic paths
try:
    devstream_root = get_devstream_root()
except RuntimeError as e:
    print(f"Error: {e}")
    sys.exit(1)
```

## Testing

### Test Dynamic Detection

```bash
# Test with custom path
DEVSTREAM_ROOT=/tmp/test ./scripts/simple-launcher.sh --help

# Test auto-detection
unset DEVSTREAM_ROOT
./scripts/simple-launcher.sh --help

# Test error handling
DEVSTREAM_ROOT=/nonexistent ./scripts/simple-launcher.sh --help
```

### Test Multi-Project

```bash
# Test different project directories
./scripts/test-multi-project.sh /path/to/project1
./scripts/test-multi-project.sh /path/to/project2

# Test from different working directories
cd /path/to/project1
./scripts/simple-launcher.sh start anthropic
```

## Troubleshooting

### Common Issues

1. **"DevStream installation not found"**
   - Set `DEVSTREAM_ROOT` environment variable
   - Ensure `start-devstream.sh` exists in installation directory
   - Check file permissions

2. **"Permission denied"**
   - Ensure scripts are executable: `chmod +x scripts/*.sh`
   - Check DevStream installation permissions

3. **"Wrong DevStream installation detected"**
   - Set `DEVSTREAM_ROOT` to correct path
   - Move installation to standard location
   - Use absolute paths in environment variable

### Debug Information

Enable debug output to see path detection:

```bash
# Shell scripts
export DEVSTREAM_DEBUG=1
./scripts/simple-launcher.sh --help

# Python scripts
python3 scripts/devstream-config.py show  # Shows detected paths
```

## Performance Considerations

The Context7 pattern is optimized for performance:

1. **Early Exit**: Returns on first successful detection
2. **Minimal File System Calls**: Checks only necessary locations
3. **Caching**: Scripts cache detected paths during execution
4. **Efficient Search**: Uses specific patterns rather than recursive search

## Security Considerations

1. **Path Validation**: Validates paths before use
2. **Permission Checks**: Ensures proper file permissions
3. **Error Handling**: Avoids exposing sensitive system information
4. **Input Sanitization**: Validates user-provided paths

---

**Generated**: 2025-10-15
**Applies to**: DevStream v2.2.0+
**Maintainer**: DevStream Development Team