from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from .models import UserProfile, PointHistory

def create_user_profile(backend, user, response, *args, **kwargs):
    request = kwargs.get('request')

    print(f"Backend: {backend.name}, User: {user}")
    if backend.name == 'google-oauth2':
        if not UserProfile.objects.filter(user=user).exists():
            # Get the full name from the response or user object
            full_name = f"{response.get('given_name', '')} {response.get('family_name', '')}".strip()
            
            # Fallback to user's first and last name if full_name is empty
            if not full_name:
                full_name = f"{user.first_name} {user.last_name}".strip()
            
            referral_code = UserProfile.generate_referral_code()
            profile = UserProfile.objects.create(
                user=user,
                full_name=full_name,
                referral_code=referral_code
            )
            print(f"UserProfile created: {profile}")

def award_daily_login_bonus(backend, user, response, *args, **kwargs):
    try:
        # Fetch the user profile
        profile = UserProfile.objects.get(user=user)
        today = now().date()

        # Check if the bonus has already been awarded today
        if profile.last_login_bonus_date != today:
            profile.aura_points += 10
            profile.last_login_bonus_date = today
            profile.save()

            # Log the transaction in PointHistory
            PointHistory.objects.create(
                user_profile=profile,
                points=10,
                reason="Daily login bonus"
            )
            print(f"Daily login bonus awarded: {profile.aura_points} Aura points")
        else:
            print("Login bonus already awarded today")
    except UserProfile.DoesNotExist:
        print(f"No user profile found for user {user.username}")