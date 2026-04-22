# JamatKhana Census Management API

## 🎯 **What This Code Does**

This is a **FastAPI-based backend system** designed to manage **census data collection** for **JamatKhanas** (religious centers) in a hierarchical organizational structure. It's essentially a **digital census management platform** that handles:

- **User Management** with role-based access control
- **Census Form Collection** and processing
- **Data Validation** and approval workflows
- **Organizational Hierarchy** management (Regional → Local → JamatKhana)

## 🏗️ **System Architecture**

### **Organizational Structure**
```
Regional Council
    └── Local Council
        └── JamatKhana (Religious Center)
            └── Census Forms
```

### **User Roles & Permissions**
1. **Enumerator (Role 1)**: Field workers who collect census data
2. **Checker (Role 2)**: Supervisors who review and approve forms
3. **Admin (Role 3)**: System administrators with full access

## 📊 **Core Features**

### **1. User Management System**
- **Authentication**: JWT-based login system
- **Role-based Access**: Different permissions for different user types
- **User Status Tracking**: Active, Inactive, Suspended
- **Password Security**: Bcrypt hashing for secure storage

### **2. Census Form Management**
- **Form Creation**: Enumerators create census forms
- **Simplified Status System**: Single status field with 4 states
  - **Pending (1)**: Form created, awaiting review
  - **Under Review (2)**: Form being reviewed by checker
  - **Approved (3)**: Form approved and completed
  - **Rejected (4)**: Form rejected with reason
- **Automatic Features**: 
  - EnumeratorId automatically set to current user
  - FormId auto-generated as "Form-JKID-Number" (e.g., Form-JK001-001)
  - FormData stores flexible JSON structures
- **Role-based Access**: Checkers can only see forms in review/completed states

### **3. Data Validation & Workflow**
- **Pydantic Models**: Automatic request/response validation
- **Business Rules**: Enumerators can only edit pending forms
- **Approval Process**: Forms go through checker review
- **Audit Trail**: Tracks who made changes and when

### **4. Organizational Hierarchy**
- **Regional Councils**: Top-level administrative units
- **Local Councils**: Mid-level units under regional councils
- **JamatKhanas**: Individual religious centers where census is conducted

## 🗄️ **Database Design**

### **Core Tables**
- **`User`**: System users with roles and permissions
- **`Form`**: Census forms with status tracking
- **`RegionalCouncil`**: Top-level organizational units
- **`LocalCouncil`**: Mid-level organizational units
- **`JamatKhana`**: Individual religious centers

### **Status & Reference Tables**
- **`Role`**: User roles (Enumerator, Checker, Admin)
- **`User_Status`**: User account status
- **`FormStatus`**: Simplified form status (Pending, Under Review, Approved, Rejected)
- **`RejectReason`**: Reasons for form rejection

### **Relationship Structure**
```
User ←→ UserJamatKhana ←→ JamatKhana
                    ↓
            LocalCouncil
                    ↓
            RegionalCouncil
```

## 🔐 **Security Features**

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt encryption for passwords
- **Role-based Authorization**: Different access levels for different roles
- **CORS Protection**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic models prevent invalid data

## 🚀 **API Endpoints**

### **Authentication**
- `POST /login` - User authentication and JWT token generation

### **User Management**
- `POST /users/` - Create new users (Admin only)
  - **Automatic ID generation**: User IDs are auto-generated in format `USER_XXXXXXXX`
  - **JamatKhanaIds array**: Assign users to multiple JamatKhanas
  - **Validation**: Checks for duplicate emails, valid JamatKhana IDs, Role IDs, and Status IDs
  - **Error handling**: Returns 400 for duplicates, invalid references, or missing data
- `GET /users/` - List users with filtering and pagination
  - **No filters**: Returns ALL users regardless of role/status
  - **With filters**: Apply role_id, status_id, email, or jamatkhana_id filters
  - **Pagination**: Use skip and limit parameters
- `GET /users/{id}` - Get specific user details
- `PUT /users/{id}` - Update user information (Admin only)
  - **Validation**: Same validation as creation, including duplicate email checks
  - **Partial updates**: Can update individual fields or entire user
- `DELETE /users/{id}` - Delete users (Admin only)

### **Form Management**
- `POST /forms/` - Create census forms (Enumerator only)
  - **Automatic EnumeratorId**: Set to current user
  - **Automatic FormId**: Generated as "Form-JKID-Number"
  - **Flexible FormData**: Accepts any JSON structure, stored as JSONB in database
  - **CNIC Validation**: Prevents duplicate applications for the same CNIC
  - **JamatKhana Validation**: Ensures JamatKhanaId exists before form creation
- **Default Status**: Set to "Pending" (1)
- `GET /forms/` - List forms with advanced filtering
  - **Role-based Access**: Role 2 (Checker) sees only review/completed forms
  - **Status Filtering**: Use form_status parameter (1=Pending, 2=Under Review, 3=Approved, 4=Rejected)
- `GET /forms/{id}` - Get specific form details
- `PUT /forms/{id}` - Update forms (role-based permissions)
  - **Enumerator**: Can edit pending forms only
  - **Checker**: Can change status to Under Review, Approved, or Rejected
  - **Rejection**: Requires RejectReasonText when status = 4
- `DELETE /forms/{id}` - Delete forms (Admin only)

### **Reference Data**
- `GET /regional-councils/` - List regional councils
- `GET /local-councils/` - List local councils (with regional filter)
- `GET /jamatkhanas/` - List JamatKhanas (with local council filter)

### **System Health**
- `GET /health` - API health check
- `GET /` - Welcome message

## 🔄 **Data Flow & Workflow**

### **Census Data Collection Process**
```
1. Enumerator Login → Get JWT Token
2. Create Census Form → Form Status: Pending (1)
3. Edit/Complete Form → Form Status: Pending (1) - can edit until reviewed
4. Checker Review → Form Status: Under Review (2) → Approved (3) or Rejected (4)
5. If Rejected → Add rejection reason and return to Enumerator
6. If Approved → Form completed and locked
```

### **User Management Workflow**
```
1. Admin Login → Get JWT Token
2. Create Enumerator/Checker Users
3. Assign Users to Specific JamatKhanas
4. Monitor User Activity and Status
5. Manage User Permissions and Access
```

## 🛠️ **Technical Implementation**

### **Backend Stack**
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: Database ORM with async support
- **PostgreSQL**: Robust relational database
- **Pydantic**: Data validation and serialization
- **JWT**: Authentication and authorization

### **Key Design Patterns**
- **Dependency Injection**: FastAPI's dependency system for database sessions
- **Repository Pattern**: SQLAlchemy models for data access
- **DTO Pattern**: Pydantic models for API requests/responses
- **Middleware Pattern**: CORS and authentication middleware

### **Async Architecture**
- **Async Database Operations**: Non-blocking database queries
- **Async Endpoints**: FastAPI async route handlers
- **Connection Pooling**: Efficient database connection management

## 📈 **Business Logic**

### **Form Approval Rules**
- **Enumerators** can only edit forms with "Pending" status (1)
- **Checkers** can change status to Under Review (2), Approved (3), or Rejected (4)
- **Rejection Requirements**: Must provide RejectReasonText when rejecting
- **Admins** have full access to all operations

### **Data Integrity**
- **Unique Constraints**: Email addresses, CNIC numbers
- **Foreign Key Relationships**: Maintains referential integrity
- **Status Validation**: Prevents invalid state transitions
- **Audit Fields**: Tracks creation and modification timestamps

### **Error Handling & Validation**
- **Duplicate Prevention**: Prevents creation of users with existing emails and forms with existing CNICs
- **Reference Validation**: Ensures JamatKhana IDs, Role IDs, and Status IDs exist
- **Data Validation**: Comprehensive input validation using Pydantic models
- **HTTP Status Codes**: Proper error responses (400 for validation, 403 for auth, 404 for not found)
- **Detailed Error Messages**: Clear error descriptions for debugging

### **Conflict Resolution**
- **Duplicate Detection**: Identifies potential duplicate entries
- **Rejection Tracking**: Records reasons for form rejection
- **Status Validation**: Prevents invalid status transitions
- **Role-based Access**: Enforces proper workflow permissions

## 🎯 **Use Cases**

### **For Enumerators**
- Collect census data from households
- Create and edit census forms
- Track form completion status
- Handle form rejections and corrections

### **For Checkers**
- Review submitted census forms
- Approve or reject forms with reasons
- Monitor data quality and consistency
- Manage form workflow

### **For Administrators**
- Manage user accounts and permissions
- Monitor system usage and performance
- Generate reports and analytics
- Configure system parameters

## 🔮 **Future Enhancements**

- **Reporting Dashboard**: Analytics and insights
- **Mobile App Support**: Offline data collection
- **Data Export**: CSV, Excel, PDF reports
- **Advanced Search**: Full-text search capabilities
- **Audit Logging**: Comprehensive activity tracking
- **API Rate Limiting**: Protection against abuse
- **Real-time Notifications**: Status change alerts

## 📚 **Getting Started**

### **Prerequisites**
- Python 3.8+
- PostgreSQL database
- Docker (optional, for containerized deployment)

### **Database Setup**
1. **Fresh Installation**: Use `init.sql` to create the database schema
2. **Migration from Old Schema**: If upgrading from the previous version, use `migrate_to_simplified_forms.sql`
   - This script migrates from the old dual-status system to the new simplified FormStatus
   - Preserves existing data while updating the schema
   - Run the migration script before starting the application

### **Quick Start**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp config.env.example .env
# Edit .env with your database credentials

# Run the application
python main.py

# Or use Docker
docker-compose up -d
```

### **Default Credentials**
- **Email**: admin@example.com
- **Password**: admin123
- **Role**: Admin

### **Role-Based Access Control**
For detailed information about user roles and permissions, see [ROLE_MAPPING.md](ROLE_MAPPING.md)

**Quick Role Reference:**
- **Role ID 1**: Enumerator (field data collection)
- **Role ID 2**: Checker (data review and approval)  
- **Role ID 3**: Admin (full system access)

## 🌟 **Why This Architecture?**

This system is designed for **scalability**, **security**, and **maintainability**:

- **Async Operations**: Handles high concurrent loads
- **Role-based Security**: Flexible permission management
- **Data Validation**: Prevents invalid data entry
- **Workflow Management**: Structured approval processes
- **Audit Trail**: Complete change tracking
- **Modular Design**: Easy to extend and modify

## 🆕 **Recent Improvements**

### **Simplified Form Status System**
- **Single Status Field**: Replaced complex dual-status system with simple 4-state workflow
- **Clear Workflow**: Pending → Under Review → Approved/Rejected
- **Better UX**: Easier to understand and manage form states

### **Enhanced User Management**
- **Automatic ID Generation**: User IDs auto-generated as USER_XXXXXXXX
- **Array Support**: JamatKhanaIds stored as PostgreSQL arrays for better performance
- **Partial Updates**: Update only the fields you need to change
- **Comprehensive Validation**: Checks for duplicates, valid references, and data integrity

### **Improved Form Management**
- **Automatic Features**: EnumeratorId and FormId automatically assigned
- **Flexible Data Storage**: FormData accepts any JSON structure, stored as JSONB in database
- **Role-based Access**: Checkers see only relevant forms
- **Better Error Handling**: Clear validation messages and proper HTTP status codes

The API serves as a **robust foundation** for digital census management, providing a **secure**, **scalable**, and **user-friendly** platform for religious community data collection and management.
