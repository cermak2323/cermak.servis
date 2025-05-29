"""add fault permissions

Revision ID: add_fault_permissions
Revises: add_missing_permission_columns
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fault_permissions'
down_revision = 'add_missing_permission_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Yeni yetki kolonlarını ekle
    with op.batch_alter_table('permissions') as batch_op:
        batch_op.add_column(sa.Column('can_view_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_add_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_edit_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_delete_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_assign_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_resolve_faults', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_add_fault_solutions', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_view_fault_history', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_manage_fault_categories', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('can_export_fault_reports', sa.Boolean(), nullable=True, default=False))

    # Varsayılan değerleri güncelle
    op.execute("""
        UPDATE permissions
        SET can_view_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN true
                ELSE false
            END,
            can_add_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN true
                ELSE false
            END,
            can_edit_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN true
                ELSE false
            END,
            can_delete_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN true
                ELSE false
            END,
            can_assign_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis')) THEN true
                ELSE false
            END,
            can_resolve_faults = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN true
                ELSE false
            END,
            can_add_fault_solutions = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis')) THEN true
                ELSE false
            END,
            can_view_fault_history = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role IN ('admin', 'muhendis', 'servis', 'musteri')) THEN true
                ELSE false
            END,
            can_manage_fault_categories = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN true
                ELSE false
            END,
            can_export_fault_reports = CASE
                WHEN user_id IN (SELECT id FROM users WHERE role = 'admin') THEN true
                ELSE false
            END
    """)


def downgrade():
    # Eklenen kolonları kaldır
    with op.batch_alter_table('permissions') as batch_op:
        batch_op.drop_column('can_view_faults')
        batch_op.drop_column('can_add_faults')
        batch_op.drop_column('can_edit_faults')
        batch_op.drop_column('can_delete_faults')
        batch_op.drop_column('can_assign_faults')
        batch_op.drop_column('can_resolve_faults')
        batch_op.drop_column('can_add_fault_solutions')
        batch_op.drop_column('can_view_fault_history')
        batch_op.drop_column('can_manage_fault_categories')
        batch_op.drop_column('can_export_fault_reports') 