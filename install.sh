#!/bin/bash
# Installation script for Home Assistant Metrics component

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📊 Home Assistant Metrics Installation Script${NC}"
echo "=============================================="

# Check if Home Assistant config directory is provided
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Usage: $0 <path-to-homeassistant-config>${NC}"
    echo "Example: $0 /config"
    echo "Example: $0 ~/.homeassistant"
    exit 1
fi

CONFIG_DIR="$1"

# Validate Home Assistant config directory
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${RED}Error: Directory $CONFIG_DIR does not exist${NC}"
    exit 1
fi

if [ ! -f "$CONFIG_DIR/configuration.yaml" ]; then
    echo -e "${RED}Error: $CONFIG_DIR does not appear to be a Home Assistant configuration directory${NC}"
    echo "configuration.yaml not found"
    exit 1
fi

# Create custom_components directory if it doesn't exist
CUSTOM_COMPONENTS_DIR="$CONFIG_DIR/custom_components"
mkdir -p "$CUSTOM_COMPONENTS_DIR"

# Create target directory
TARGET_DIR="$CUSTOM_COMPONENTS_DIR/home_assistant_metrics"
mkdir -p "$TARGET_DIR"

echo -e "${GREEN}✅ Installing Home Assistant Metrics to $TARGET_DIR${NC}"

# Copy component files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
COMPONENT_SOURCE="$SCRIPT_DIR/custom_components/home_assistant_metrics"

if [ ! -d "$COMPONENT_SOURCE" ]; then
    echo -e "${RED}Error: Component source directory not found at $COMPONENT_SOURCE${NC}"
    echo "Make sure you're running this script from the repository root"
    exit 1
fi

# Copy all files
cp -r "$COMPONENT_SOURCE"/* "$TARGET_DIR/"

echo -e "${GREEN}✅ Component files copied successfully${NC}"

# Set appropriate permissions
chmod -R 644 "$TARGET_DIR"
find "$TARGET_DIR" -type d -exec chmod 755 {} \;

echo -e "${GREEN}✅ Permissions set${NC}"

# Display next steps
echo ""
echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Restart Home Assistant"
echo "2. Go to Settings > Devices & Services"
echo "3. Click 'Add Integration'"
echo "4. Search for 'Home Assistant Metrics'"
echo "5. Follow the configuration wizard"
echo ""
echo "Documentation:"
echo "- README.md - General setup and usage"
echo "- CONFIGURATION.md - Detailed configuration guide" 
echo "- EXAMPLES.md - Grafana dashboard examples"
echo ""
echo -e "${YELLOW}⚠️  Remember to restart Home Assistant before configuring the integration!${NC}"