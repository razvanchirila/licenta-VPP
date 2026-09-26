import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/services/solar_forecast_service.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_cards.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_day_selector.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_labels.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_total_card.dart';
import 'package:flutter_interface/widgets/solar_forecast/hourly_production_chart.dart';

class SolarForecastScreen extends StatefulWidget {
  const SolarForecastScreen({super.key});

  @override
  State<SolarForecastScreen> createState() => _SolarForecastScreenState();
}

class _SolarForecastScreenState extends State<SolarForecastScreen> {
  SolarForecastResult? _result;
  bool _isLoading = true;
  String? _selectedDate;

  @override
  void initState() {
    super.initState();
    _loadForecast();
  }

  Future<void> _loadForecast({bool forceRefresh = false}) async {
    setState(() => _isLoading = true);
    final result = await solarForecastService.getForecast(forceRefresh: forceRefresh);
    if (!mounted) return;
    setState(() {
      _result = result;
      _isLoading = false;
      if (result.hasData && _selectedDate == null) {
        final dates = result.data!.availableDates;
        if (dates.isNotEmpty) _selectedDate = dates.first;
      }
    });
  }

  /// A forced refresh costs one of the 12 hourly API calls, so confirm first.
  void _showRefreshWarning() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surfaceAlt,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('Actualizare date', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600)),
        content: Text(
          'API-ul are o limită de 12 request-uri/oră. Sigur vrei să actualizezi?',
          style: GoogleFonts.inter(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Anulează', style: GoogleFonts.inter(color: Colors.white54)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _loadForecast(forceRefresh: true);
            },
            child: Text('Actualizează', style: GoogleFonts.inter(color: AppColors.amber)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.deepBackground,
      appBar: AppBar(
        backgroundColor: AppColors.deepBackground,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: Column(
          children: [
            Text(
              'Predicții Solare',
              style: GoogleFonts.inter(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600),
            ),
            if (_result?.fromCache == true)
              Text(
                ForecastLabels.timeSinceUpdate(_result?.timestamp, DateTime.now()),
                style: GoogleFonts.inter(color: Colors.white54, fontSize: 12),
              ),
          ],
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            onPressed: _showRefreshWarning,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.amber));
    }
    final result = _result;
    if (result?.hasError == true && result?.hasData != true) {
      return ForecastMessage(
        icon: Icons.cloud_off_rounded,
        message: result?.error ?? 'Eroare necunoscută',
        onRetry: () => _loadForecast(forceRefresh: true),
      );
    }
    final data = result?.data;
    final selected = _selectedDate;
    if (data == null || selected == null) {
      return const ForecastMessage(
        icon: Icons.wb_sunny_outlined,
        message: 'Nu sunt disponibile predicții pentru această locație',
      );
    }

    final now = DateTime.now();
    final isToday = selected == ForecastLabels.ymd(now);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (result?.rateLimited == true)
            const ForecastBanner(
              icon: Icons.warning_rounded,
              color: AppColors.red,
              text: 'Limită API depășită. Se afișează date din cache.',
            ),
          if (result?.networkError == true)
            const ForecastBanner(
              icon: Icons.wifi_off_rounded,
              color: AppColors.amber,
              text: 'Fără conexiune. Se afișează date din cache.',
            ),
          ForecastDaySelector(dates: data.availableDates, selected: selected, onSelected: _selectDate),
          const SizedBox(height: 20),
          ForecastTotalCard(
            totalKwh: data.getTotalKwhForDate(selected),
            dayLabel: isToday ? 'azi' : ForecastLabels.dayLabel(selected, now),
          ),
          const SizedBox(height: 20),
          HourlyProductionChart(
            selectedDate: selected,
            hourlyKw: data.getHourlyKwForDate(selected),
            maxKw: data.maxHourlyKw,
            peakHours: data.getPeakHoursForDate(selected).toSet(),
            isToday: isToday,
          ),
          const SizedBox(height: 20),
          PeakHoursCard(peakHours: data.getPeakHoursForDate(selected)),
          const SizedBox(height: 20),
          DailyForecastList(forecasts: data.dailyForecasts, selectedDate: selected, onSelected: _selectDate),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  void _selectDate(String date) => setState(() => _selectedDate = date);
}
