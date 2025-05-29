from main import app
from database import db
from models import User, Permission

def update_user_permissions():
    with app.app_context():
        # Tüm kullanıcıları al
        users = User.query.all()
        
        for user in users:
            # Kullanıcının yetkilerini al
            permission = Permission.query.filter_by(user_id=user.id).first()
            
            if permission:
                # Kullanıcının rolüne göre can_list_machines yetkisini güncelle
                if user.role in ['admin', 'servis', 'muhendis', 'musteri']:
                    permission.can_list_machines = True
                    print(f"Updated permissions for user {user.username} (role: {user.role})")
            else:
                # Eğer kullanıcının yetkisi yoksa, varsayılan yetkilerle oluştur
                permission = Permission(
                    user_id=user.id,
                    can_view_machines=True,
                    can_list_machines=True,
                    can_view_parts=True,
                    can_view_faults=True,
                    can_view_contact=True
                )
                db.session.add(permission)
                print(f"Created new permissions for user {user.username} (role: {user.role})")
        
        try:
            db.session.commit()
            print("All permissions updated successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating permissions: {e}")

if __name__ == '__main__':
    update_user_permissions() 