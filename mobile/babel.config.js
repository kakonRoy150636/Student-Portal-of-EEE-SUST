module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
    // Reanimated's plugin has to stay last in the plugin list.
    plugins: ['react-native-reanimated/plugin'],
  };
};
