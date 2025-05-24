
from main import app
from models import db, MaintenanceReminderSettings

def update_maintenance_settings():
    with app.app_context():
        # Clear existing settings
        MaintenanceReminderSettings.query.delete()

        # Bakım aralıkları ve bildirim günleri
        maintenance_settings = [
            # TB215R, TB216, TB217R için ayarlar (50 saat ilk bakım)
            {'machine_type': 'TB215R', 'first_maintenance_hours': 50, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB216', 'first_maintenance_hours': 50, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB217R', 'first_maintenance_hours': 50, 'hours_interval': 250, 'notify_before_days': 7},
            
            # Diğer makineler için ayarlar (250 saat ilk bakım)
            {'machine_type': 'TB325R', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB235-2', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB240-2', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB260-2', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TB290-2', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
            {'machine_type': 'TL8R-2', 'first_maintenance_hours': 250, 'hours_interval': 250, 'notify_before_days': 7},
        ]

        for setting in maintenance_settings:
            reminder_setting = MaintenanceReminderSettings(
                machine_type=setting['machine_type'],
                first_maintenance_hours=setting['first_maintenance_hours'],
                hours_interval=setting['hours_interval'],
                notify_before_days=setting['notify_before_days'],
                is_active=True
            )
            db.session.add(reminder_setting)

        db.session.commit()

if __name__ == '__main__':
    update_maintenance_settings()
