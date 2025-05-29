-- Machine Management
ALTER TABLE permission ADD COLUMN can_delete_machines BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_export_machines BOOLEAN DEFAULT 0;

-- Maintenance Management
ALTER TABLE permission ADD COLUMN can_delete_maintenance BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_view_maintenance_history BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_manage_maintenance_schedules BOOLEAN DEFAULT 0;

-- Equipment Management
ALTER TABLE permission ADD COLUMN can_add_equipment BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_edit_equipment BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_delete_equipment BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_manage_equipment_status BOOLEAN DEFAULT 0;

-- Parts and Catalog Management
ALTER TABLE permission ADD COLUMN can_manage_catalogs BOOLEAN DEFAULT 0;

-- Fault Management
ALTER TABLE permission ADD COLUMN can_add_faults BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_edit_faults BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_delete_faults BOOLEAN DEFAULT 0;

-- Offer Management
ALTER TABLE permission ADD COLUMN can_edit_offers BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_delete_offers BOOLEAN DEFAULT 0;

-- Warranty and Accounting
ALTER TABLE permission ADD COLUMN can_manage_warranty BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_manage_accounting BOOLEAN DEFAULT 0;

-- System Management
ALTER TABLE permission ADD COLUMN can_manage_roles BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_manage_system_settings BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_view_logs BOOLEAN DEFAULT 0;

-- Reporting
ALTER TABLE permission ADD COLUMN can_view_reports BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_create_reports BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_export_reports BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_view_statistics BOOLEAN DEFAULT 0;

-- File Management
ALTER TABLE permission ADD COLUMN can_delete_files BOOLEAN DEFAULT 0;

-- Communication and Notifications
ALTER TABLE permission ADD COLUMN can_send_notifications BOOLEAN DEFAULT 0;
ALTER TABLE permission ADD COLUMN can_manage_announcements BOOLEAN DEFAULT 0; 