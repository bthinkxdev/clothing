# 🎭 Demo Mode Setup Guide

## Quick Start

The OTP demo mode is **already enabled** and ready to use!

## 📱 How to Use (Demo Flow)

### Step 1: Navigate to Login
Go to: `http://your-domain/auth/login/`

### Step 2: Enter Phone Number
- Enter any phone number (e.g., `+91 9000000000`)
- Must pass validation

### Step 3: Click "Send OTP"
- Click the "Send OTP" button
- Wait for success message

### Step 4: **AUTOMATIC** ✨
The script will automatically:
1. ✅ Fill OTP field with `123456`
2. ✅ Show green border on input
3. ✅ Display demo message
4. ✅ Click "Verify & Login" button after 1 second
5. ✅ Log you in!

## 🎨 Visual Indicators

You'll see these indicators when demo mode is active:

### 1. Floating Badge (Top-Right)
```
🎭 DEMO MODE - OTP will auto-fill as 123456
```
- Red gradient background
- Pulsing animation
- Always visible on auth pages

### 2. Auto-Fill Message
```
🎭 DEMO: Auto-filled OTP (123456)
```
- Green background
- Appears below OTP input
- Disappears after verification

### 3. Green Border
- OTP input field gets green border when auto-filled
- Visual confirmation of demo mode

### 4. Console Logs
Open browser console to see:
```
🎭 DEMO MODE: Auto-OTP enabled
🎭 DEMO MODE: Send OTP clicked, waiting for response...
🎭 DEMO MODE: OTP sent detected, auto-filling...
🎭 DEMO MODE: OTP filled with 123456
🎭 DEMO MODE: Auto-clicking verify button...
```

## 🔧 Configuration

### Current Setup
The demo script is included in:
- ✅ `templates/auth/login.html`
- ✅ `templates/auth/otp_verify.html`

### Files Added
```
static/js/auth-demo.js          (Main demo script)
static/js/DEMO-README.md        (Technical documentation)
DEMO-SETUP-GUIDE.md             (This file)
```

## ⚙️ Backend Requirements

For this demo to work, your backend must:

1. **Accept any OTP for demo purposes**
   - Check if OTP is `123456`
   - Allow login with this demo OTP
   - OR disable OTP validation in development

2. **Return success message**
   - Backend should send success response
   - Message should include "OTP sent" or "check your phone"

### Example Backend Code (Django)

```python
# In your OTP verify view
def otp_verify(request):
    otp = request.POST.get('otp')
    
    # DEMO MODE: Accept 123456 as valid OTP
    if otp == '123456':
        # Log user in
        user = get_or_create_user(phone)
        login(request, user)
        return JsonResponse({'success': True, 'redirect': '/'})
    
    # ... rest of your OTP validation logic
```

## 🚫 Disabling Demo Mode

### Method 1: Comment Out (Recommended)
Edit `templates/auth/login.html` and `templates/auth/otp_verify.html`:
```html
<!-- <script src="{% static 'js/auth-demo.js' %}"></script> -->
```

### Method 2: Delete Files
```bash
rm static/js/auth-demo.js
rm static/js/DEMO-README.md
rm DEMO-SETUP-GUIDE.md
```

### Method 3: Rename File
```bash
mv static/js/auth-demo.js static/js/auth-demo.js.disabled
```

## 🐛 Troubleshooting

### Demo not working?

**Check 1: Script loaded?**
- Open browser DevTools → Network tab
- Look for `auth-demo.js`
- Should show 200 status

**Check 2: Console errors?**
- Open browser Console
- Look for errors or warnings
- Should see demo mode messages

**Check 3: OTP send successful?**
- Make sure "OTP sent" message appears
- Backend must return success response
- Check Network tab for `/auth/otp/send/` request

**Check 4: Status message correct?**
Script looks for these keywords:
- "otp sent"
- "check your phone"

If your backend returns different message, update the script:
```javascript
// In auth-demo.js, line ~50
if (statusText.includes('otp sent') || statusText.includes('your custom message')) {
```

### Backend not accepting 123456?

Update your backend to accept this demo OTP:
```python
# Django example
if settings.DEBUG and otp == '123456':
    return JsonResponse({'success': True})
```

### Want different demo OTP?

Edit `static/js/auth-demo.js`:
```javascript
// Line ~67
otpInput.value = '123456'; // Change to your preferred OTP
```

## 📊 Testing Checklist

Before presenting demo:

- [ ] Navigate to login page
- [ ] Verify "DEMO MODE" badge is visible
- [ ] Enter phone number
- [ ] Click "Send OTP"
- [ ] Confirm OTP auto-fills
- [ ] Confirm auto-verification works
- [ ] Check successful login/redirect

## ⚠️ Production Deployment

### Pre-Production Checklist

Before going live:

- [ ] Remove demo script from templates
- [ ] Delete `auth-demo.js` file
- [ ] Remove demo OTP acceptance from backend
- [ ] Test real OTP flow
- [ ] Verify SMS/Email delivery
- [ ] Check authentication logs

## 🎬 Demo Tips

### For Best Demo Experience:

1. **Keep browser console open** - Shows demo activity
2. **Use incognito/private window** - Fresh session
3. **Test before presentation** - Ensure everything works
4. **Have backup plan** - Manual OTP entry if demo fails
5. **Mention it's demo mode** - Be transparent with clients

### Client Presentation Script:

> "For this demonstration, we've implemented an auto-fill feature 
> that simulates the OTP verification process. In production, 
> users would receive a real OTP via SMS, but for demo purposes, 
> the system automatically enters the verification code."

## 📞 Support

For issues or questions:
- Check `static/js/DEMO-README.md` for technical details
- Review console logs for debugging
- Contact development team

---

**Happy Demoing! 🎭**

Remember: This is for DEMONSTRATION ONLY - remove before production!


