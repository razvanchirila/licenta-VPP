class HouseImageSelector {
  static const String dayLightsOff = 'assets/casa_zi_fara_lumini.png';

  static const String nightLightsOn = 'assets/casa_noapte_lumini.png';

  static const String dayLightsOn = 'assets/casa_zi_lumini.png';

  static const String nightLightsOff = 'assets/casa_noapte_fara_lumini.png';

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
