# 🚀 JamatKhana Census API - Enhanced Postman Collection

## 📋 Overview

This enhanced Postman collection provides comprehensive testing capabilities for the JamatKhana Census API, with a special focus on **user filtering and management**. The collection includes detailed examples, documentation, and pre-configured requests for all major API endpoints.

## 🎯 Key Features

- **🔐 Complete Authentication Flow** - Login endpoints with JWT token handling
- **👥 Advanced User Management** - CRUD operations with comprehensive filtering
- **📊 User Filtering Examples** - Multiple filter combinations and use cases
- **📝 Form Management** - Complete census form lifecycle management
- **🔍 Lookup Tables** - Reference data for forms and user management
- **📚 Documentation** - Built-in guides and examples

## 🚀 Quick Start

### 1. Import the Collection

1. Open Postman
2. Click "Import" button
3. Select the `JamatKhana_API_Postman_Collection.json` file
4. The collection will be imported with all endpoints and examples

### 2. Set Up Environment Variables

The collection includes pre-configured environment variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `base_url` | API base URL | `http://localhost:8000` |
| `access_token` | JWT access token | (empty - set after login) |
| `user_email` | Default user email | `admin@example.com` |
| `user_password` | Default user password | `admin123` |
| `jamatkhana_id` | Test JamatKhana ID | `JK001` |

### 3. Authentication

1. **Login First**: Use the "Login" endpoint under Authentication
2. **Copy Token**: Copy the `access_token` from the response
3. **Set Token**: Paste it into the `access_token` environment variable
4. **Test Endpoints**: All other endpoints will now work with authentication

## 👥 User Management & Filtering

### 🔍 Available User Filters

The API supports the following query parameters for user filtering:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `role_id` | integer | Filter by user role | `?role_id=1` |
| `status_id` | integer | Filter by account status | `?status_id=1` |
| `email` | string | Partial email match | `?email=admin` |
| `jamatkhana_id` | string | Filter by assigned JamatKhana | `?jamatkhana_id=JK001` |
| `skip` | integer | Pagination offset | `?skip=10` |
| `limit` | integer | Maximum records | `?limit=20` |

### 🎭 User Roles

| Role ID | Role Name | Description |
|---------|-----------|-------------|
| 1 | Enumerator | Data collector for census forms |
| 2 | Checker | Data reviewer and approver |
| 3 | Admin | System administrator |

### 📊 User Status

| Status ID | Status Name | Description |
|-----------|-------------|-------------|
| 1 | Active | User account is active |
| 2 | Inactive | User account is inactive |
| 3 | Suspended | User account is suspended |

### 🔍 Filter Examples

#### Basic Filters

```bash
# Get all active enumerators
GET /users/?role_id=1&status_id=1

# Find users by email pattern
GET /users/?email=@gmail.com

# Get users assigned to specific JamatKhana
GET /users/?jamatkhana_id=JK001
```

#### Advanced Filters

```bash
# Get active enumerators in JK001 with pagination
GET /users/?role_id=1&status_id=1&jamatkhana_id=JK001&skip=0&limit=50

# Find users with 'john' in email, max 20 results
GET /users/?email=john&limit=20

# Get users from page 3 (50 per page)
GET /users/?skip=100&limit=50
```

#### Multiple Filter Combinations

```bash
# Find active enumerators with email containing 'enum'
GET /users/?role_id=1&status_id=1&email=enum&skip=0&limit=50

# Find inactive admins
GET /users/?role_id=3&status_id=2

# Find checkers in specific JamatKhana
GET /users/?role_id=2&jamatkhana_id=JK001
```

## 📝 Form Management

### 🔄 Form Lifecycle

1. **Create Form** - Enumerator creates census form
2. **Edit Form** - Enumerator can edit pending forms
3. **Submit for Review** - Form status changes to "Under Review"
4. **Approve/Reject** - Checker reviews and approves or rejects
5. **Complete** - Approved forms are locked

### 📊 Form Status

| Status ID | Status Name | Description |
|-----------|-------------|-------------|
| 1 | Pending | Form is being filled/edited |
| 2 | Under Review | Form submitted for review |
| 3 | Approved | Form approved and completed |
| 4 | Rejected | Form rejected with reason |

## 🧪 Testing Scenarios

### 1. User Management Testing

```bash
# Test user creation
POST /users/ - Create new user with role and JamatKhana

# Test user filtering
GET /users/?role_id=1&status_id=1 - Get active enumerators
GET /users/?email=admin - Find users by email pattern

# Test user updates
PUT /users/{id} - Update user details
DELETE /users/{id} - Delete user (Admin only)
```

### 2. Form Management Testing

```bash
# Test form creation
POST /forms/ - Create census form (Enumerator)

# Test form workflow
PUT /forms/{id} - Edit form (Pending status)
PUT /forms/{id} - Submit for review
PUT /forms/{id} - Approve/reject (Checker)
```

### 3. Authentication Testing

```bash
# Test login
POST /login - Get JWT token

# Test protected endpoints
GET /users/ - Requires valid token
```

## 🔧 Environment Setup

### Local Development

```bash
# Set base URL for local development
base_url = http://localhost:8000

# Use test credentials
user_email = admin@example.com
user_password = admin123
```

### Production

```bash
# Set base URL for production
base_url = https://your-api-domain.com

# Use production credentials
user_email = your-production-email
user_password = your-production-password
```

## 📊 Response Examples

### User Response Format

```json
{
  "Id": "USER_12345678",
  "Email": "user@example.com",
  "FullName": "User Name",
  "PhoneNumber": "+1234567890",
  "RoleId": 1,
  "StatusId": 1,
  "JamatKhanaIds": ["JK001"],
  "IsActive": true,
  "CreatedAt": "2024-01-01T00:00:00Z",
  "UpdatedAt": "2024-01-01T00:00:00Z"
}
```

### User List Response

```json
[
  {
    "Id": "USER_12345678",
    "Email": "enumerator@example.com",
    "FullName": "John Doe",
    "RoleId": 1,
    "StatusId": 1,
    "JamatKhanaIds": ["JK001"],
    "IsActive": true
  }
]
```

## 🚨 Common Issues & Solutions

### 1. Authentication Errors

**Problem**: `401 Unauthorized` errors
**Solution**: 
- Ensure you've logged in first
- Copy the `access_token` from login response
- Set the `access_token` environment variable

### 2. Filter Not Working

**Problem**: Filters not returning expected results
**Solution**:
- Check parameter names (use `role_id`, not `roleId`)
- Verify parameter values (e.g., `role_id=1` not `role_id="1"`)
- Check if the filter combination is valid

### 3. Pagination Issues

**Problem**: Getting wrong page of results
**Solution**:
- `skip` starts from 0 (first page = skip=0)
- `limit` controls maximum records returned
- Page calculation: `skip = (page_number - 1) * limit`

## 📚 Additional Resources

- **API Documentation**: Check the main README.md for complete API specs
- **Database Schema**: Review the database models in main.py
- **Role Mapping**: See ROLE_MAPPING.md for detailed role permissions

## 🤝 Contributing

To enhance this collection:

1. Add new endpoints as needed
2. Include comprehensive examples
3. Update documentation
4. Test all requests before committing

## 📞 Support

For issues with the API or collection:

1. Check the API logs for errors
2. Verify environment variables are set correctly
3. Ensure the API server is running
4. Review the authentication flow

---

**Happy Testing! 🎉**

This collection provides everything you need to test the JamatKhana Census API comprehensively, with a focus on user management and filtering capabilities.
