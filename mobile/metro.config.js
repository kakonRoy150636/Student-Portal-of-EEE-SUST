const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const config = getDefaultConfig(__dirname);

// NativeWind v4 compiles global.css through Metro; without this wrapper the
// `className` props resolve to nothing and every screen renders unstyled.
module.exports = withNativeWind(config, { input: './global.css' });
