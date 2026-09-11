/// Utility class for selecting the appropriate house image based on state.
///
/// This class provides a pure function for determining which house image
/// to display based on the current weather mode (day/night) and lighting
/// state (on/off).
class HouseImageSelector {
  // Image asset path constants for all 4 combinations
  
  /// Day mode with lights off
  static const String dayLightsOff = 'assets/casa_zi_fara_lumini.png';
  
  /// Night mode with lights on
  static const String nightLightsOn = 'assets/casa_noapte_lumini.png';
  
  /// Day mode with lights on
  static const String dayLightsOn = 'assets/casa_zi_lumini.png';
  
  /// Night mode with lights off
  static const String nightLightsOff = 'assets/casa_noapte_fara_lumini.png';

  /// Pure function to determine house image based on state.
  ///
  /// [isDayMode] - true for day/sunny mode, false for night/rainy mode
  /// [lightsOn] - true if lights are on, false if lights are off
  ///
  /// Returns the appropriate image asset path based on the combination
  /// of weather mode and lighting state.
  ///
  /// Image State Matrix:
  /// | Weather Mode | Lights State | Image Asset |
  /// |-------------|--------------|-------------|
  /// | Day (sunny) | OFF | casa_zi_fara_lumini.png |
  /// | Day (sunny) | ON | casa_zi_lumini.png |
  /// | Night (rainy) | OFF | casa_noapte_fara_lumini.png |
  /// | Night (rainy) | ON | casa_noapte_lumini.png |
  static String getImagePath({
    required bool isDayMode,
    required bool lightsOn,
  }) {
    if (isDayMode) {
      return lightsOn ? dayLightsOn : dayLightsOff;
    } else {
      return lightsOn ? nightLightsOn : nightLightsOff;
    }
  }
}
