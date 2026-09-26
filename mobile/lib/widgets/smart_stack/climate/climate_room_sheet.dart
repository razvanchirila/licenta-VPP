import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/climate_settings.dart';

class ClimateRoomSheet extends StatelessWidget {
  final ClimateRoom selectedRoom;
  final Function(ClimateRoom) onRoomSelected;

  const ClimateRoomSheet({super.key, required this.selectedRoom, required this.onRoomSelected});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceAlt.withValues(alpha: 0.95),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: Colors.grey.shade600, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 20),
          Text('Selectează Camera',
              style: GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 20),
          ...ClimateRoom.values.map(
              (room) => _RoomTile(room: room, isSelected: room == selectedRoom, onTap: () => onRoomSelected(room))),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _RoomTile extends StatelessWidget {
  final ClimateRoom room;
  final bool isSelected;
  final VoidCallback onTap;

  const _RoomTile({required this.room, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: isSelected ? AppColors.blue.withValues(alpha: 0.2) : AppColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: isSelected ? AppColors.blue.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.08)),
            ),
            child: Row(
              children: [
                Icon(room.icon, color: isSelected ? AppColors.blue : Colors.white.withValues(alpha: 0.6), size: 22),
                const SizedBox(width: 12),
                Text(room.displayName,
                    style: GoogleFonts.inter(
                        color: isSelected ? Colors.white : Colors.white.withValues(alpha: 0.8),
                        fontSize: 15,
                        fontWeight: FontWeight.w500)),
                const Spacer(),
                if (isSelected) const Icon(Icons.check_circle_rounded, color: AppColors.blue, size: 22),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
