# Odoo Module - Face Registration API

## New API Endpoint for Face Registration

I've added a new API endpoint that allows Odoo to send face images for registration:

### Endpoint

```
POST /api/v1/persons/{person_id}/register-face
```

### Authentication

Requires `person:write` permission via `X-API-Key` or `Authorization: Bearer` header

### Request

```json
{
  "image": "base64_encoded_image_data",
  "force_update": false  // Optional
}
```

**Image Format:**
- Base64 encoded image
- Can include data URI prefix (`data:image/jpeg;base64,`) or just the base64 string
- Supported formats: JPEG, PNG, BMP

### Response

**Success (201):**
```json
{
  "success": true,
  "message": "Face registered successfully for John Doe",
  "data": {
    "person_id": "FP00001",
    "name": "John Doe",
    "face_id": "2025-01-15T10:30:00",
    "image_path": "/path/to/face/image.jpg",
    "total_faces": 25
  }
}
```

**Error Responses:**

**404 - Person Not Found:**
```json
{
  "success": false,
  "error": "Person not found",
  "message": "Person with ID FP00001 not found"
}
```

**400 - Missing Image:**
```json
{
  "success": false,
  "error": "Missing image data",
  "message": "image field is required"
}
```

**422 - No Face Detected:**
```json
{
  "success": false,
  "error": "No face detected",
  "message": "No face was detected in the provided image"
}
```

**422 - Cannot Encode Face:**
```json
{
  "success": false,
  "error": "Could not encode face",
  "message": "Face was detected but could not be encoded"
}
```

---

## How It Works

### 1. Person Must Exist First

Before registering a face, the person must exist in the system. Odoo should create/sync the person first:

```bash
# Step 1: Create person via Odoo sync
POST /api/v1/persons
{
  "person_id": "FP00001",
  "name": "John Doe",
  "email": "john@example.com",
  "department": "Engineering"
}
```

### 2. Then Register Face

After person exists, Odoo can send the face image:

```bash
# Step 2: Register face
POST /api/v1/persons/FP00001/register-face
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

### 3. What Happens

When you call this endpoint:

1. ✅ **Person Retrieved** - Gets person from attendance system
2. ✅ **Image Decoded** - Decodes base64 image
3. ✅ **Face Detection** - Detects face in image using face_recognition
4. ✅ **Face Encoding** - Creates 128-D face encoding
5. ✅ **Save to Face Database** - Stores encoding in faces.pkl
6. ✅ **Update Recognizer** - Adds to live recognizer (immediate effect!)
7. ✅ **Update Person Record** - Updates person with face info
8. ✅ **Ready for Recognition** - Person can now be recognized by camera

---

## Example Usage from Odoo

### Python Example (from Odoo)

```python
import base64
import requests

# Read image file
with open('/path/to/face/photo.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Or if you have image bytes directly
# image_data = base64.b64encode(image_bytes).decode('utf-8')

# Send to API
response = requests.post(
    'http://192.168.50.152:5000/api/v1/persons/FP00001/register-face',
    headers={
        'Authorization': 'Bearer your_api_key_here',
        'Content-Type': 'application/json'
    },
    json={
        'image': image_data,
        'force_update': False
    }
)

result = response.json()
if result.get('success'):
    print(f"Face registered: {result['data']}")
else:
    print(f"Error: {result.get('error')}")
```

### JavaScript Example (from Odoo Web)

```javascript
// Assuming you have image as base64
const imageBase64 = "..."; // Your base64 image data

fetch('http://192.168.50.152:5000/api/v1/persons/FP00001/register-face', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        image: imageBase64,
        force_update: false
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Face registered:', data.data);
    } else {
        console.error('Error:', data.error);
    }
});
```

---

## Integration with Odoo Module

### From Odoo `attendance.person` Model

Add this method to your Odoo person model:

```python
def action_register_face_from_image(self):
    """
    Register face for this person using image from Odoo.
    Called when user uploads face photo in Odoo.
    """
    self.ensure_one()

    if not self.server_id:
        raise UserError("No API server configured for this person")

    if not self.face_image:  # Assume you have a Binary field for face image
        raise UserError("No face image uploaded")

    # Get base64 image
    image_base64 = self.face_image.decode('utf-8') if isinstance(self.face_image, bytes) else self.face_image

    # Call API
    endpoint = f"/api/v1/persons/{self.external_person_id}/register-face"
    response = self.server_id._make_request(
        method='POST',
        endpoint=endpoint,
        data={
            'image': image_base64,
            'force_update': False
        }
    )

    if response.get('success'):
        self.write({
            'face_registered': True,
            'face_registered_at': fields.Datetime.now(),
            'sync_status': 'synced'
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f"Face registered for {self.name}",
                'type': 'success',
            }
        }
    else:
        raise UserError(f"Failed to register face: {response.get('error')}")
```

### Add Button to Odoo View

```xml
<record id="view_attendance_person_form" model="ir.ui.view">
    <field name="name">attendance.person.form</field>
    <field name="model">attendance.person</field>
    <field name="arch" type="xml">
        <form>
            <header>
                <button name="action_register_face_from_image"
                        type="object"
                        string="📸 Register Face"
                        class="oe_highlight"
                        attrs="{'invisible': [('face_registered', '=', True)]}"/>
            </header>
            <sheet>
                <!-- Person fields -->
                <group>
                    <field name="name"/>
                    <field name="external_person_id"/>
                    <field name="face_image" widget="image"/>
                    <field name="face_registered" readonly="1"/>
                </group>
            </sheet>
        </form>
    </field>
</record>
```

---

## Workflow

### Complete End-to-End Flow

```
1. HR adds employee in Odoo
   ↓
2. Odoo syncs employee to Face API
   POST /api/v1/persons
   ↓
3. HR uploads face photo in Odoo
   (Binary field: face_image)
   ↓
4. HR clicks "Register Face" button
   ↓
5. Odoo sends image to API
   POST /api/v1/persons/{person_id}/register-face
   ↓
6. API processes image:
   • Detects face
   • Creates encoding
   • Saves to database
   • Updates recognizer
   ↓
7. Face is ready for recognition!
   ↓
8. Employee approaches camera
   ↓
9. Face recognized automatically
   ↓
10. Attendance marked in Face API
   ↓
11. Odoo pulls attendance record
   GET /api/v1/attendance
   ↓
12. Attendance appears in Odoo
```

---

## Testing the API

### Test 1: Create Person

```bash
curl -X POST http://192.168.50.152:5000/api/v1/persons \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "TEST001",
    "name": "Test User",
    "email": "test@example.com",
    "department": "Testing"
  }'
```

### Test 2: Register Face

First, get a base64 image:
```bash
base64 face_photo.jpg > face_base64.txt
```

Then send it:
```bash
curl -X POST http://192.168.50.152:5000/api/v1/persons/TEST001/register-face \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"image\": \"$(cat face_base64.txt)\"
  }"
```

### Test 3: Verify Registration

Check if person has face:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://192.168.50.152:5000/api/v1/persons/TEST001
```

Response should include face info in metadata.

---

## Error Handling

### Best Practices in Odoo

```python
def register_face_safe(self):
    """
    Safe face registration with proper error handling
    """
    try:
        result = self.action_register_face_from_image()
        return result
    except UserError as e:
        # Known errors
        _logger.warning(f"Face registration failed for {self.name}: {e}")
        raise
    except Exception as e:
        # Unexpected errors
        _logger.error(f"Unexpected error registering face for {self.name}: {e}")
        raise UserError("An unexpected error occurred. Check system logs.")
```

### Common Issues

**Issue: "Person not found"**
- Solution: Ensure person was synced from Odoo first
- Check: `GET /api/v1/persons/{person_id}`

**Issue: "No face detected"**
- Solution: Ensure image shows a clear face
- Image should be well-lit, front-facing
- Face should be at least 50x50 pixels

**Issue: "Could not encode face"**
- Solution: Image quality might be too low
- Try with higher resolution image
- Ensure face is clearly visible

**Issue: "Invalid image data"**
- Solution: Check base64 encoding is correct
- Ensure image format is supported (JPEG, PNG, BMP)

---

## Security Considerations

### 1. API Key Security
- Use dedicated API key for Odoo
- Grant only required permissions: `person:write`
- Rotate keys regularly

### 2. Image Data
- Images are processed immediately and discarded
- Only face encodings are stored permanently
- Original images saved to disk (can be disabled)

### 3. Rate Limiting
- Consider rate limiting in production
- Prevent abuse of face registration endpoint

### 4. Validation
- API validates person exists before processing
- API validates face is detected before encoding
- All errors logged for auditing

---

## Performance

### Expected Performance

- **Image Upload**: < 100ms
- **Face Detection**: 100-500ms (depending on image size)
- **Face Encoding**: 50-200ms
- **Total Time**: < 1 second typically

### Optimization Tips

1. **Image Size**: Send images around 800x600px
2. **Batch Processing**: For multiple persons, process sequentially
3. **Async in Odoo**: Use Odoo's job queue for non-blocking operation

---

## Summary

✅ **New Endpoint**: `POST /api/v1/persons/{person_id}/register-face`
✅ **Odoo Compatible**: Works with Bearer token authentication
✅ **Base64 Images**: Accepts base64 encoded images
✅ **Immediate Effect**: Face available for recognition instantly
✅ **Complete Integration**: Works with existing attendance system
✅ **Error Handling**: Comprehensive error messages
✅ **Production Ready**: Tested and documented

The API is now ready for Odoo to control face registration!

For UI integration, I can also add a "Persons Management" tab to the web console if needed, but since Odoo will control everything via API, the web UI is optional.
