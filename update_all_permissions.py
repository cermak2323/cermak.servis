from main import app
from database import db
from models import User, Permission

def update_all_permissions():
    with app.app_context():
        # Tüm kullanıcıları al
        users = User.query.all()
        
        # Rol bazlı varsayılan yetkiler
        servis_permissions = {
            "can_view_machines": True,
            "can_add_machines": True,
            "can_edit_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_add_maintenance": True,
            "can_edit_maintenance": True,
            "can_view_maintenance_reminders": True,
            "can_view_equipment": True,
            "can_add_equipment": True,
            "can_edit_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_view_catalogs": True,
            "can_view_offers": True,
            "can_create_offers": True,
            "can_view_periodic_maintenance": True,
            "can_view_contact": True
        }

        muhendis_permissions = {
            "can_view_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_equipment": True,
            "can_edit_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_edit_parts": True,
            "can_view_catalogs": True,
            "can_manage_catalogs": True,
            "can_view_offers": True,
            "can_approve_offers": True,
            "can_reject_offers": True,
            "can_view_periodic_maintenance": True,
            "can_manage_periodic_maintenance": True,
            "can_view_contact": True,
            "can_view_purchase_prices": True,
            "can_view_warranty": True,
            "can_view_accounting": True
        }

        musteri_permissions = {
            "can_view_machines": True,
            "can_search_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_equipment": True,
            "can_view_parts": True,
            "can_view_offers": True,
            "can_view_contact": True
        }

        admin_permissions = {
            "can_view_machines": True,
            "can_add_machines": True,
            "can_edit_machines": True,
            "can_delete_machines": True,
            "can_search_machines": True,
            "can_export_machines": True,
            "can_list_machines": True,
            "can_view_maintenance": True,
            "can_add_maintenance": True,
            "can_edit_maintenance": True,
            "can_delete_maintenance": True,
            "can_view_maintenance_history": True,
            "can_view_maintenance_reminders": True,
            "can_manage_maintenance_schedules": True,
            "can_view_equipment": True,
            "can_add_equipment": True,
            "can_edit_equipment": True,
            "can_delete_equipment": True,
            "can_manage_equipment_status": True,
            "can_view_parts": True,
            "can_edit_parts": True,
            "can_view_catalogs": True,
            "can_manage_catalogs": True,
            "can_view_purchase_prices": True,
            "can_view_offers": True,
            "can_create_offers": True,
            "can_edit_offers": True,
            "can_delete_offers": True,
            "can_approve_offers": True,
            "can_reject_offers": True,
            "can_view_periodic_maintenance": True,
            "can_manage_periodic_maintenance": True,
            "can_view_contact": True,
            "can_view_warranty": True,
            "can_view_accounting": True,
            "can_view_admin_panel": True,
            "can_manage_users": True,
            "can_upload_excel": True
        }

        role_permissions = {
            'servis': servis_permissions,
            'muhendis': muhendis_permissions,
            'musteri': musteri_permissions,
            'admin': admin_permissions
        }

        for user in users:
            # Kullanıcının yetkilerini al veya oluştur
            permission = Permission.query.filter_by(user_id=user.id).first()
            if not permission:
                permission = Permission(user_id=user.id)
                db.session.add(permission)

            # Kullanıcının rolüne göre yetkileri güncelle
            if user.role in role_permissions:
                permissions_to_set = role_permissions[user.role]
                for perm_name, perm_value in permissions_to_set.items():
                    setattr(permission, perm_name, perm_value)
                print(f"Updated permissions for user {user.username} (role: {user.role})")
            else:
                print(f"Warning: Unknown role {user.role} for user {user.username}")

        try:
            db.session.commit()
            print("All permissions updated successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating permissions: {e}")

if __name__ == '__main__':
    update_all_permissions() 