# Role ID Mapping & Permissions

## 🔐 **Role Definitions**

| Role ID | Role Name | Description | Permissions |
|---------|-----------|-------------|-------------|
| **1** | **Enumerator** | Field worker who collects census data | • Create census forms<br>• Edit pending forms<br>• View own forms<br>• Submit forms for review |
| **2** | **Checker** | Supervisor who reviews and approves forms | • View all forms<br>• Approve/reject forms<br>• Add rejection reasons<br>• Monitor form progress |
| **3** | **Admin** | System administrator with full access | • All permissions<br>• User management<br>• System configuration<br>• Data deletion |

## 👥 **Sample Users (Auto-created)**

### **Enumerator (Role ID: 1)**
- **Email**: `enumerator@example.com`
- **Password**: `enum123`
- **Permissions**: Form creation and editing
- **Linked to**: JK001 (Sample JamatKhana)

### **Checker (Role ID: 2)**
- **Email**: `checker@example.com`
- **Password**: `checker123`
- **Permissions**: Form review and approval
- **Linked to**: JK001 (Sample JamatKhana)

### **Admin (Role ID: 3)**
- **Email**: `admin@example.com`
- **Password**: `admin123`
- **Permissions**: Full system access
- **Linked to**: All JamatKhanas

## 🔗 **Database Linkages**

### **Role Table**
```sql
INSERT INTO "Role" ("Id", "Name") VALUES 
(1, 'Enumerator'),
(2, 'Checker'),
(3, 'Admin');
```

### **User-Role Relationship**
```sql
-- Users are linked to roles via RoleId foreign key
User.RoleId → Role.Id
```

### **User-JamatKhana Relationship**
```sql
-- Users are linked to JamatKhanas via UserJamatKhana junction table
User.Id ←→ UserJamatKhana.UserId
UserJamatKhana.JamatKhanaId ←→ JamatKhana.Id
```

## 📋 **Permission Matrix**

| Action | Enumerator (1) | Checker (2) | Admin (3) |
|--------|----------------|-------------|-----------|
| **Login** | ✅ | ✅ | ✅ |
| **View Own Profile** | ✅ | ✅ | ✅ |
| **Create Forms** | ✅ | ❌ | ✅ |
| **Edit Forms** | ✅ (Pending only) | ❌ | ✅ |
| **Approve/Reject Forms** | ❌ | ✅ | ✅ |
| **View All Forms** | ❌ | ✅ | ✅ |
| **Create Users** | ❌ | ❌ | ✅ |
| **Delete Users** | ❌ | ❌ | ✅ |
| **System Configuration** | ❌ | ❌ | ✅ |

## 🚀 **Testing Different Roles**

### **1. Test as Enumerator**
```bash
# Login as enumerator
POST /login
username: enumerator@example.com
password: enum123

# Create a form (should work)
POST /forms/
Authorization: Bearer {enumerator_token}
```

### **2. Test as Checker**
```bash
# Login as checker
POST /login
username: checker@example.com
password: checker123

# Approve a form (should work)
PUT /forms/{form_id}
Authorization: Bearer {checker_token}
```

### **3. Test as Admin**
```bash
# Login as admin
POST /login
username: admin@example.com
password: admin123

# Create a new user (should work)
POST /users/
Authorization: Bearer {admin_token}
```

## 🔍 **Role Validation in Code**

The system validates roles in several places:

```python
# Example: Only admins can create users
if current_user.RoleId != 3:  # Admin role
    raise HTTPException(status_code=403, detail="Not authorized")

# Example: Only enumerators can create forms
if current_user.RoleId != 1:  # Enumerator role
    raise HTTPException(status_code=403, detail="Not authorized")
```

## 📊 **Status Flow by Role**

### **Enumerator Workflow**
```
1. Create Form → Status: Pending
2. Edit Form → Status: In Progress
3. Submit Form → Status: Completed
4. If Rejected → Back to Pending
```

### **Checker Workflow**
```
1. Review Form → Status: Under Review
2. Approve Form → Status: Approved
3. Reject Form → Status: Rejected + Reason
```

### **Admin Workflow**
```
1. Monitor all activities
2. Manage users and permissions
3. Configure system settings
4. Handle data maintenance
```

## 🎯 **Key Points**

- **Role ID 1 = Enumerator**: Field data collection
- **Role ID 2 = Checker**: Data review and approval
- **Role ID 3 = Admin**: Full system management
- **All roles are properly linked** in the database
- **Sample users are created** for each role
- **Permissions are enforced** at the API level
- **Role-based access control** is implemented throughout
