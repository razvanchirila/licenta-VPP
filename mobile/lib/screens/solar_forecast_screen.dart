import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/services/solar_forecast_service.dart';
import 'package:flutter_interface/models/solar_forecast_data.dart';

class SolarForecastScreen extends StatefulWidget {
  const SolarForecastScreen({super.key});

  @override
  State<SolarForecastScreen> createState() => _SolarForecastScreenState();
}

class _SolarForecastScreenState extends State<SolarForecastScreen> {
  SolarForecastResult? _result;
  bool _isLoading = true;
  String? _selectedDate;
  int? _touchedHour;

  @override
  void initState() {
    super.initState();
    _loadForecast();
  }

  Future<void> _loadForecast({bool forceRefresh = false}) async {
    setState(() => _isLoading = true);
    
    final result = await solarForecastService.getForecast(forceRefresh: forceRefresh);
    
    if (mounted) {
      setState(() {
        _result = result;
        _isLoading = false;
        // Set default selected date to today
        if (result.hasData && _selectedDate == null) {
          final dates = result.data!.availableDates;
          if (dates.isNotEmpty) {
            _selectedDate = dates.first;
          }
        }
      });
    }
  }

  String _getTimeSinceUpdate() {
    if (_result?.timestamp == null) return '';
    
    final diff = DateTime.now().difference(_result!.timestamp!);
    if (diff.inMinutes < 1) return 'Actualizat acum';
    if (diff.inMinutes < 60) return 'Actualizat acum ${diff.inMinutes} min';
    if (diff.inHours < 24) return 'Actualizat acum ${diff.inHours} ore';
    return 'Actualizat acum ${diff.inDays} zile';
  }

  void _showRefreshWarning() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A1A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Actualizare date',
          style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600),
        ),
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
            child: Text('Actualizează', style: GoogleFonts.inter(color: const Color(0xFFFBBF24))),
          ),
        ],
      ),
    );
  }

  String _formatDateLabel(String dateStr) {
    final now = DateTime.now();
    final todayStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    final tomorrowStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${(now.day + 1).toString().padLeft(2, '0')}';
    
    if (dateStr == todayStr) return 'Azi';
    if (dateStr == tomorrowStr) return 'Mâine';
    
    final dt = DateTime.tryParse(dateStr);
    if (dt == null) return dateStr;
    
    final weekdays = ['Lun', 'Mar', 'Mie', 'Joi', 'Vin', 'Sâm', 'Dum'];
    return '${weekdays[dt.weekday - 1]} ${dt.day}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0A0A0A),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: Column(
          children: [
            Text(
              'Predicții Solare',
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (_result?.fromCache == true)
              Text(
                _getTimeSinceUpdate(),
                style: GoogleFonts.inter(
                  color: Colors.white54,
                  fontSize: 12,
                ),
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
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFFBBF24)),
      );
    }

    if (_result?.hasError == true && _result?.hasData != true) {
      return _buildErrorState();
    }

    if (_result?.hasData != true) {
      return _buildEmptyState();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_result?.rateLimited == true) _buildRateLimitBanner(),
          if (_result?.networkError == true) _buildNetworkErrorBanner(),
          
          // Day selector
          _buildDaySelector(),
          const SizedBox(height: 20),
          
          // Selected day total card
          _buildSelectedDayTotalCard(),
          const SizedBox(height: 20),
          
          // Interactive hourly chart
          _buildInteractiveChart(),
          const SizedBox(height: 20),
          
          // Peak hours recommendation
          _buildPeakHoursCard(),
          const SizedBox(height: 20),
          
          // Daily forecasts list
          _buildDailyForecasts(),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildDaySelector() {
    final data = _result!.data!;
    final dates = data.availableDates;

    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: dates.length,
        padding: const EdgeInsets.symmetric(horizontal: 4),
        itemBuilder: (context, index) {
          final date = dates[index];
          final isSelected = date == _selectedDate;
          
          return GestureDetector(
            onTap: () => setState(() {
              _selectedDate = date;
              _touchedHour = null;
            }),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: isSelected ? const Color(0xFFFBBF24) : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
              ),
              alignment: Alignment.center,
              child: Text(
                _formatDateLabel(date),
                style: GoogleFonts.inter(
                  color: isSelected ? Colors.black : Colors.white70,
                  fontSize: 14,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSelectedDayTotalCard() {
    final data = _result!.data!;
    final totalKwh = data.getTotalKwhForDate(_selectedDate!);
    final isToday = _selectedDate == data.availableDates.first;
    
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                const Color(0xFFFBBF24).withOpacity(0.2),
                const Color(0xFFF59E0B).withOpacity(0.1),
              ],
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFFBBF24).withOpacity(0.3)),
          ),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: const Color(0xFFFBBF24).withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.wb_sunny_rounded, color: Color(0xFFFBBF24), size: 32),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Producție estimată ${isToday ? "azi" : _formatDateLabel(_selectedDate!)}',
                      style: GoogleFonts.inter(color: Colors.white70, fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          totalKwh.toStringAsFixed(1),
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontSize: 36,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'kWh',
                          style: GoogleFonts.inter(
                            color: Colors.white70,
                            fontSize: 18,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInteractiveChart() {
    final data = _result!.data!;
    final hourlyKw = data.getHourlyKwForDate(_selectedDate!);
    final maxKw = data.maxHourlyKw;
    final currentHour = DateTime.now().hour;
    final peakHours = data.getPeakHoursForDate(_selectedDate!);
    final isToday = _selectedDate == data.availableDates.first;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Producție orară',
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              // Show touched value
              if (_touchedHour != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFBBF24).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${_touchedHour.toString().padLeft(2, '0')}:00 - ${(hourlyKw[_touchedHour] ?? 0).toStringAsFixed(2)} kW',
                    style: GoogleFonts.inter(
                      color: const Color(0xFFFBBF24),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              final chartWidth = constraints.maxWidth;
              final barWidth = (chartWidth - 48) / 24; // 24 bars with spacing
              
              return GestureDetector(
                onHorizontalDragUpdate: (details) {
                  final localX = details.localPosition.dx;
                  final hour = ((localX / chartWidth) * 24).clamp(0, 23).toInt();
                  if (hour != _touchedHour) {
                    setState(() => _touchedHour = hour);
                  }
                },
                onTapDown: (details) {
                  final localX = details.localPosition.dx;
                  final hour = ((localX / chartWidth) * 24).clamp(0, 23).toInt();
                  setState(() => _touchedHour = hour);
                },
                onTapUp: (_) => setState(() => _touchedHour = null),
                onHorizontalDragEnd: (_) => setState(() => _touchedHour = null),
                child: SizedBox(
                  height: 200,
                  child: Column(
                    children: [
                      // Chart bars area
                      Expanded(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: List.generate(24, (hour) {
                            final kw = hourlyKw[hour] ?? 0;
                            final heightPercent = maxKw > 0 ? (kw / maxKw) : 0.0;
                            final isCurrentHour = isToday && hour == currentHour;
                            final isPeakHour = peakHours.contains(hour);
                            final isTouched = hour == _touchedHour;

                            return Expanded(
                              child: Container(
                                margin: const EdgeInsets.symmetric(horizontal: 1),
                                alignment: Alignment.bottomCenter,
                                // Bar - fixed height calculation
                                child: Container(
                                  height: (160 * heightPercent).clamp(3.0, 160.0),
                                      decoration: BoxDecoration(
                                    color: isTouched
                                        ? const Color(0xFFFBBF24)
                                        : isCurrentHour
                                            ? const Color(0xFF3B82F6)
                                            : isPeakHour
                                                ? const Color(0xFFFBBF24)
                                                : const Color(0xFFFBBF24).withOpacity(0.4),
                                    borderRadius: BorderRadius.circular(2),
                                    boxShadow: isTouched
                                        ? [
                                            BoxShadow(
                                              color: const Color(0xFFFBBF24).withOpacity(0.5),
                                              blurRadius: 8,
                                              spreadRadius: 1,
                                            )
                                          ]
                                        : null,
                                  ),
                                ),
                              ),
                            );
                          }),
                        ),
                      ),
                      const SizedBox(height: 8),
                      // Hour labels - separate row for alignment
                      Row(
                        children: List.generate(24, (hour) {
                          final isCurrentHour = isToday && hour == currentHour;
                          final isTouched = hour == _touchedHour;
                          
                          return Expanded(
                            child: hour % 4 == 0
                                ? Text(
                                    '$hour',
                                    textAlign: TextAlign.center,
                                    style: GoogleFonts.inter(
                                      color: isTouched
                                          ? const Color(0xFFFBBF24)
                                          : isCurrentHour
                                              ? const Color(0xFF3B82F6)
                                              : Colors.white38,
                                      fontSize: 10,
                                      fontWeight: isTouched ? FontWeight.w600 : FontWeight.w400,
                                    ),
                                  )
                                : const SizedBox.shrink(),
                          );
                        }),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          // Legend and hint
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  if (isToday) ...[
                    _buildLegendItem(const Color(0xFF3B82F6), 'Acum'),
                    const SizedBox(width: 12),
                  ],
                  _buildLegendItem(const Color(0xFFFBBF24), 'Vârf'),
                ],
              ),
              Text(
                'Atinge graficul pentru detalii',
                style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 4),
        Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 11)),
      ],
    );
  }

  Widget _buildPeakHoursCard() {
    final data = _result!.data!;
    final peakHours = data.getPeakHoursForDate(_selectedDate!);

    if (peakHours.isEmpty) return const SizedBox.shrink();

    final peakHoursStr = peakHours.map((h) => '${h.toString().padLeft(2, '0')}:00').join(', ');

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF22C55E).withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF22C55E).withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: const Color(0xFF22C55E).withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.tips_and_updates_rounded, color: Color(0xFF22C55E), size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Recomandare',
                  style: GoogleFonts.inter(
                    color: const Color(0xFF22C55E),
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Folosește aparatele cu consum mare între orele $peakHoursStr pentru a maximiza autoconsumul.',
                  style: GoogleFonts.inter(color: Colors.white70, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDailyForecasts() {
    final data = _result!.data!;
    final forecasts = data.dailyForecasts;

    if (forecasts.isEmpty) return const SizedBox.shrink();

    final maxKwh = forecasts.map((f) => f.kWh).reduce((a, b) => a > b ? a : b);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Toate zilele',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        ...forecasts.map((forecast) => _buildDayCard(forecast, maxKwh)),
      ],
    );
  }

  Widget _buildDayCard(DailyForecast forecast, double maxKwh) {
    final percent = maxKwh > 0 ? (forecast.kWh / maxKwh) : 0.0;
    final isSelected = forecast.date == _selectedDate;
    
    return GestureDetector(
      onTap: () => setState(() {
        _selectedDate = forecast.date;
        _touchedHour = null;
      }),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFFFBBF24).withOpacity(0.15)
              : const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected
                ? const Color(0xFFFBBF24).withOpacity(0.5)
                : Colors.white.withOpacity(0.1),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    if (forecast.isToday)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFBBF24),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'AZI',
                          style: GoogleFonts.inter(
                            color: Colors.black,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    Text(
                      forecast.formattedDate,
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                Text(
                  '${forecast.kWh.toStringAsFixed(1)} kWh',
                  style: GoogleFonts.inter(
                    color: isSelected ? const Color(0xFFFBBF24) : Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: percent,
                backgroundColor: Colors.white.withOpacity(0.1),
                valueColor: AlwaysStoppedAnimation(
                  isSelected ? const Color(0xFFFBBF24) : const Color(0xFFFBBF24).withOpacity(0.5),
                ),
                minHeight: 6,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded, color: Colors.white38, size: 64),
            const SizedBox(height: 16),
            Text(
              _result?.error ?? 'Eroare necunoscută',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 16),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _loadForecast(forceRefresh: true),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reîncearcă'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFBBF24),
                foregroundColor: Colors.black,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wb_sunny_outlined, color: Colors.white38, size: 64),
            const SizedBox(height: 16),
            Text(
              'Nu sunt disponibile predicții pentru această locație',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRateLimitBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEF4444).withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFEF4444).withOpacity(0.5)),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_rounded, color: Color(0xFFEF4444), size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Limită API depășită. Se afișează date din cache.',
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNetworkErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFBBF24).withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFBBF24).withOpacity(0.5)),
      ),
      child: Row(
        children: [
          const Icon(Icons.wifi_off_rounded, color: Color(0xFFFBBF24), size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Fără conexiune. Se afișează date din cache.',
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
