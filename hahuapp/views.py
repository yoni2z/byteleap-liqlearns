from datetime import timedelta
import base64
from django.core.files.base import ContentFile
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .forms import (
    UserRegisterForm, 
    UserLoginForm, 
    UserProfileForm, 
    WordCharadeForm, 
    WritingSubmissionForm, 
    VideoForm, 
    ParagraphAudioForm, 
    VoiceRecordingForm,
    EventForm,
    LetterSoundForm,
    WordAudioForm,
    WordVideoForm,

    LevelForm, ModuleForm, SlideForm, SlideContentForm, SlideQuestionForm # for the lecture slide
)

from .models import UserProfile, Event, LetterVideo, LetterImage, BingoQuestion, LetterSoundSequence, DescriptiveImage, DescriptiveSentenceQuestion, FillInTheBlank, Numbers, Video, VideoResponse, WordAudioRecording, Paragraph
from django.utils import timezone
from django.utils.timezone import now
import random
import numpy as np # for the word hunt part
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator

# for the payment sections
import stripe
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
####################

from .models import (
    PointHistory,

    LetterSound, # for the letter sound memory game
    WordAudio,
    WordVideo,
    WordCharade,
    WordCountdownRecording,
    Sentence,
    Passage,
    
    SentenceSynonym,
    SentencePunctuation,
    ParagraphCreation,
    AmharicLetterFamily, AmharicLetterAudio,
    LetterFillIn,
    NumberToWord,
    AmharicEnglishMatching,
    Story,
    StoryPart,
    StoryQuestion,
    Level, Module, Slide, SlideContent, SlideQuestion, UserSlideProgress, UserLevelProgress, UserModuleProgress
)

from .utils import (
    get_random_questions,
)

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            user_profile = UserProfile.objects.create(
                user=user,
                full_name=form.cleaned_data['full_name'],
                referral_code=UserProfile.generate_referral_code()
            )

            # Process the referral code if provided
            referral_code = form.cleaned_data.get('referral_code')
            if referral_code:
                referrer = UserProfile.objects.filter(referral_code=referral_code).first()
                if referrer:
                    user_profile.referred_by = referrer  # Link the referrer
                    user_profile.save()

            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'signup.html', {'form': form})

def user_login(request):
    error = ''
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                # Daily login bonus logic
                user_profile = UserProfile.objects.get(user=user)
                today = now().date()
                if user_profile.last_login_bonus_date != today:
                    # Award 10 Aura points
                    user_profile.aura_points += 10
                    user_profile.last_login_bonus_date = today
                    user_profile.save()

                    # Log the transaction in PointHistory
                    PointHistory.objects.create(
                        user_profile=user_profile,
                        points=10,
                        reason="Daily login bonus"
                    )

                return redirect('home')
            else:
                error = 'Invalid username or password.'  # Set the error message
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form, 'error': error})

@login_required
def user_profile(request):
    user_profile = UserProfile.objects.get(user=request.user)
    all_users = list(UserProfile.objects.filter(is_subscribed=True).order_by('-aura_points'))
    rank = all_users.index(user_profile) + 1 if user_profile in all_users else None

    # Pass user profile data to the template context
    return render(request, 'user_profile.html', {
        'full_name': user_profile.full_name,
        'rank': rank,
        'level': user_profile.level,
        'aura_points': user_profile.aura_points,
        'referral_code': user_profile.referral_code,
    })

# for the point system

@login_required
def award_points(request):
    if request.method == "POST":
        try:
            # Retrieve the points and reason from the request body
            data = json.loads(request.body)
            points = data.get('points', 0)
            reason = data.get('reason', '')

            # Get the user profile for the logged-in user
            user_profile = UserProfile.objects.get(user=request.user)

            # Update the user's aura points
            user_profile.aura_points += points
            user_profile.save()

            # Create a record in PointHistory
            PointHistory.objects.create(
                user_profile=user_profile,
                points=points,
                reason=reason
            )

            return JsonResponse({'message': 'Points awarded successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'message': 'Invalid request method'}, status=400)

# for the point system


def user_logout(request):
    logout(request)
    return redirect('login')


def event_list(request):
    events = Event.objects.filter(start_date__gte=timezone.now()).order_by('start_date')
    return render(request, 'event_list.html', {'events': events})

def latest_event(request):
    # Fetch the latest upcoming event based on the start date
    latest_event = Event.objects.filter(start_date__gte=timezone.now()).order_by('start_date').first()
    users = UserProfile.objects.filter(is_subscribed=True).order_by('-aura_points')
    top_3 = users[:3]
    levels = Level.objects.order_by('order') ###### 

    return render(request, 'home.html', {
        'latest_event': latest_event,
        'top_3': top_3,
        'levels': levels,
        })


### ---------- for the payment page -------------- ### 

stripe.api_key = settings.STRIPE_SECRET_KEY

from django.urls import reverse
from django.http import HttpResponseRedirect

def payment_page(request):
    level = None
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'GET':
        level_id = request.GET.get('level_id')  # Use `level_id` instead of `plan_id`
        if level_id:
            level = get_object_or_404(Level, id=level_id)

            # Check if the level is already unlocked or paid for
            if user_profile.related_level and user_profile.related_level.id == level.id:
                message = "You have already purchased this level."
                return HttpResponseRedirect(reverse('error_page') + f'?message={message}')

            # Check prerequisites only for levels above the current unlocked level
            if user_profile.related_level:
                if level.order > user_profile.related_level.order + 1:
                    message = "You must complete the previous level before purchasing this one."
                    return HttpResponseRedirect(reverse('error_page') + f'?message={message}')
            elif level.order != 1:  # If no levels are unlocked, only allow the first level to be purchased
                message = "You must start with the first level."
                return HttpResponseRedirect(reverse('error_page') + f'?message={message}')

        return render(request, 'payment.html', {
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'level_name': level.name,
            'price': level.price,
            'level_id': level_id
        })

    if request.method == 'POST':
        level_id = request.POST.get('level_id')  # Use `level_id` instead of `plan_id`
        if not level_id:
            return JsonResponse({'error': 'Invalid level selected.'})

        level = get_object_or_404(Level, id=level_id)

        # Prevent duplicate payments
        if user_profile.related_level and user_profile.related_level.id == level.id:
            return JsonResponse({'error': 'You have already purchased this level.'})

        # Verify prerequisites only for levels above the current unlocked level
        if user_profile.related_level:
            if level.order > user_profile.related_level.order + 1:
                return JsonResponse({'error': 'You must complete the previous level before purchasing this one.'})
        elif level.order != 1:  # If no levels are unlocked, only allow the first level to be purchased
            return JsonResponse({'error': 'You must start with the first level.'})

        try:
            success_url = request.build_absolute_uri(f'/payment/success/?level_id={level_id}')
            cancel_url = request.build_absolute_uri('/payment/cancel/')

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': level.name,
                        },
                        'unit_amount': int(level.price * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
            )

            return JsonResponse({'id': session.id})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    return render(request, 'payment.html', {'error': 'Invalid level selected.'})

@login_required
def success(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Ensure the user paid for a valid level
    level_id = request.GET.get('level_id')  # Pass the level_id in the success URL
    if not level_id:
        message = "Invalid level selected."
        return HttpResponseRedirect(reverse('error_page') + f'?message={message}')

    level = get_object_or_404(Level, id=level_id)

    # Prevent duplicate unlocks
    user_level_progress, created = UserLevelProgress.objects.get_or_create(
        user=request.user, 
        level=level
    )

    if not created and not user_level_progress.is_locked:
        message = "This level is already unlocked."
        return HttpResponseRedirect(reverse('error_page') + f'?message={message}')

    # Unlock the level for the user
    user_level_progress.is_locked = False
    user_level_progress.save()

    # Update the user's profile to reflect the latest unlocked level
    user_profile.level = level.name
    user_profile.related_level = level
    user_profile.is_subscribed = True  # Mark as subscribed
    user_profile.save()

    # Unlock the first module in the unlocked level (if applicable)
    first_module = level.modules.order_by('order').first()
    if first_module:
        UserModuleProgress.objects.get_or_create(
            user=request.user,
            module=first_module,
            defaults={'is_locked': False}  # Unlock the first module automatically
        )

    # Award 100 Aura points only for first subscription (if applicable)
    if not PointHistory.objects.filter(user_profile=user_profile, reason="Welcome Bonus").exists():
        user_profile.aura_points = int(user_profile.aura_points or 0) + 100
        user_profile.save()

        # Log the transaction in PointHistory
        PointHistory.objects.create(
            user_profile=user_profile,
            points=100,
            reason="Welcome Bonus"
        )

    # Handle Referral Points
    referrer = user_profile.referred_by  # Use already established referrer
    if referrer:
        # Check if referral bonus for this referred student has already been awarded
        referral_reason = f"Referral Bonus: Payment completed by {user_profile.full_name}"
        if not PointHistory.objects.filter(user_profile=referrer, reason=referral_reason).exists():
            if referrer.successful_referrals_this_week() < 3:  # Weekly cap check
                referrer.aura_points += 25
                referrer.save()
                PointHistory.objects.create(
                    user_profile=referrer,
                    points=25,
                    reason=referral_reason
                )

    # Handle Downline Bonus Cap
    referrer = user_profile.referred_by  # Start with the direct referrer
    points_map = [0, 15, 5]  # Points for levels 2 and 3 (Level 1 handled by direct referral bonus above)
    level_idx = 0

    while referrer and level_idx < len(points_map):
        if level_idx > 0:  # Skip Level 1 to avoid conflict with Weekly Referral Cap
            downline_reason = f"Downline Bonus: Payment completed by {user_profile.full_name} (Level {level_idx + 1})"
            if not PointHistory.objects.filter(user_profile=referrer, reason=downline_reason).exists():
                referrer.aura_points += points_map[level_idx]
                referrer.save()

                # Log the transaction in PointHistory
                PointHistory.objects.create(
                    user_profile=referrer,
                    points=points_map[level_idx],
                    reason=downline_reason
                )

        # Move to the next referrer in the chain
        referrer = referrer.referred_by
        level_idx += 1

    return render(request, 'payment_success.html')

def cancel(request):
    return render(request, 'payment_cancel.html')

def error_page(request):
    message = request.GET.get('message', 'An error occurred.')
    return render(request, 'error_page.html', {'message': message})

# Letter Bingo game Start

def letter_bingo_view(request):
    # Fetch all stored letters from the database
    letters = list(LetterSound.objects.values_list('letter', flat=True))

    # Ensure there are enough letters for the game logic
    if len(letters) < 4:
        return render(request, 'error.html', {'message': 'Not enough letters in the database.'})

    # Select a random letter to display
    random_letter = random.choice(letters)

    # Generate 4 choices, including the correct one
    choices = random.sample(letters, 3)
    if random_letter not in choices:
        choices.append(random_letter)
    random.shuffle(choices)

    return render(request, 'letter_bingo.html', {
        'random_letter': random_letter,
        'choices': choices
    })

# Letter Bingo Game View end

# Letter Memory Game Start

def letter_memory_view(request):
    letters = list(LetterSound.objects.values_list('letter', flat=True))
    selected_letters = random.sample(letters, 6)  # Select 6 unique letters (can adjust number)
    card_set = selected_letters * 2  # Duplicate the letters to create pairs
    random.shuffle(card_set)  # Shuffle the cards to randomize their positions

    return render(request, 'letter_memory.html', {'card_set': card_set})

# Letter Memory Game End

# Letter Sequencing Game Start

def letter_sequencing_view(request):
    letters = list(LetterSound.objects.values_list('letter', flat=True))
    selected_letters = random.sample(letters, 5)  # Select 5 unique letters

    # Sort letters to get the correct order
    correct_order = sorted(selected_letters)

    return render(request, 'letter_sequencing.html', {
        'question_type': 'letter_sequencing',
        'selected_letters': selected_letters,
        'correct_order': json.dumps(correct_order),
        'cor_order': correct_order
    })

# Letter Sequencing Game End

# Letter Fill in the Blank Game Start

def letter_fill_in_the_blanks_view(request):
    words_data = LetterFillIn.objects.all()
    
    selected_word = random.choice(words_data)

    context = {
        'correct_word': selected_word.correct_word,
        'display_word': selected_word.display_word,
        'choices': selected_word.choices,
        'correct_letter': selected_word.correct_letter,
        'meaning': selected_word.meaning,
    }

    return render(request, 'letter_fill_in_the_blanks.html', context)

# letter fill in the blank game end

# letter sound discrimination start

def letter_sound_discrimination_view(request):
    word_sounds = list(LetterSound.objects.all())

    if len(word_sounds) < 4:
        return render(request, 'error.html', {'message': 'Not enough sounds to play the game.'})

    odd_sound = random.choice(word_sounds)
    other_sounds = [s for s in word_sounds if s.letter != odd_sound.letter]

    # Pick three identical sounds
    identical_sound = random.choice(other_sounds)
    game_sounds = [identical_sound.sound_field.url] * 3 + [odd_sound.sound_field.url]

    # Shuffle the sounds for display
    random.shuffle(game_sounds)

    game_data = {
        "sounds": game_sounds,
        "correct": odd_sound.sound_field.url,
        "odd": odd_sound.letter,
        "others": identical_sound.letter,
    }

    return render(request, 'letter_sound_discrimination.html', {'game_data': game_data})

# letter sound discrimination end

# letter Sound Memory start 

def letter_sound_memory_view(request):
    sounds = list(LetterSound.objects.all())
    selected_sounds = random.sample(sounds, 6)  # 3 pairs (6 cards)
    card_data = selected_sounds * 2  # Duplicate for matching pairs
    random.shuffle(card_data)  # Shuffle cards

    return render(request, 'letter_sound_memory.html', {'card_data': card_data})

# letter sound Memory End

# letter sound charades

def letter_sound_charades_view(request):
    sounds = LetterSound.objects.all()
    selected_sound = random.choice(sounds)

    # Create letter choices (1 correct, 3 incorrect)
    correct_letter = selected_sound.letter
    other_sounds = LetterSound.objects.exclude(letter=correct_letter)
    incorrect_choices = random.sample(list(other_sounds), 3)

    # Combine correct and incorrect choices, and shuffle them
    choices = [correct_letter] + [sound.letter for sound in incorrect_choices]
    random.shuffle(choices)

    context = {
        'selected_sound': selected_sound,
        'choices': choices,
    }
    return render(request, 'letter_sound_charades.html', context)

# letter sound charades end

# letter story start

def letter_story_view(request):
    letters = LetterSound.objects.all()
    
    selected_letters = random.sample(list(letters), 5)
    return render(request, 'letter_story.html', {'selected_letters': selected_letters})

# letter story end

# letter fill in the blank 2 

def letter_fill_in_the_blanks_2_view(request):
    words_data = LetterFillIn.objects.all()
    
    selected_word = random.choice(words_data)

    context = {
        'correct_word': selected_word.correct_word,
        'display_word': selected_word.display_word,
        'choices': selected_word.choices,
        'correct_letter': selected_word.correct_letter,
        'meaning': selected_word.meaning,
    }

    return render(request, 'letter_fill_in_the_blanks_2.html', context)

# letter fill in the blank 2 end

# word formation start

def word_formation_view(request):
    words_data = [
        {
            "base_word": "ንቁ", 
            "prefixes": ["እ", "ባ", "ሌ"], 
            "suffixes": ["ነት", "ላል", "ዉ"], 
            "correct_prefix": "እ", 
            "correct_suffix": "ላል", 
            "formed_word": "እንቁላል", 
            "meaning": "An egg"
        },
        {
            "base_word": "ስጋ", 
            "prefixes": ["እ", "መ", "ም"], 
            "suffixes": ["ዊ", "ና", "ብ"], 
            "correct_prefix": "ም", 
            "correct_suffix": "ና", 
            "formed_word": "ምስጋና", 
            "meaning": "Gratitude"
        },
    ]

    selected_word = random.choice(words_data)
    random.shuffle(selected_word["prefixes"])
    random.shuffle(selected_word["suffixes"])

    context = {
        'base_word': selected_word['base_word'],
        'prefixes': selected_word['prefixes'],
        'suffixes': selected_word['suffixes'],
        'correct_prefix': selected_word['correct_prefix'],
        'correct_suffix': selected_word['correct_suffix'],
        'formed_word': selected_word['formed_word'],
        'meaning': selected_word['meaning'],
    }

    return render(request, 'word_formation.html', context)

# word formation end

# scrambled letters start 

def scrambled_letters_view(request):
    # Select 5 different letters randomly
    letters = list(LetterSound.objects.values_list('letter', flat=True))
    selected_letters = random.sample(letters, 5)  # Select 5 unique letters
    scrambled = scramble_word(''.join(selected_letters))  # Scramble the letters

    return render(request, 'scrambled_letters.html', {
        'scrambled_word': scrambled,
    })

def scramble_word(word):
    scrambled = list(word)
    random.shuffle(scrambled)
    return ''.join(scrambled)

# scrambled letters end

# timed writing start

def timed_writing_view(request):
    # Predefined list of writing challenges
    challenges = [
        "ከአንተ ጋር አልስማማም፡፡",
        "ተጨማሪ ጊዜ እፈልጋለሁ!",
        "የውሳኔ ሃሳቦች በስብሰባው ላይ ተቀባይነት አግኝተዋል፡፡",
        "በዚህ ሐይቅ ውስጥ ብዙ ዓሦች አሉ፡፡",
        "በሚቀጥለው ጊዜ መቼ ማየት እችላለሁ?"
    ]
    
    # Randomly select a challenge
    challenge = random.choice(challenges)

    context = {
        'target_text': challenge,
    }
    return render(request, 'timed_writing.html', context)

# timed writing end

# listen and write start

def listen_and_write_view(request):
    letter_sound = random.choice(LetterSound.objects.all())

    context = {
        'letter_sound': letter_sound,
    }
    return render(request, 'listen_and_write.html', context)

# listen and write end

# audio recognition start

def audio_recognition_view(request):
    # Select a random WordAudio object
    word_audio = random.choice(WordAudio.objects.all())
    context = {
        'word_audio': word_audio,
    }
    return render(request, 'audio_recognition.html', context)

# audio recognition end

# letter quiz start

def letter_quiz_view(request):
    """
    Letter quiz view that:
    - Plays exactly 5 sounds.
    - Displays exactly 15 letter choices (including correct ones).
    """
    # Step 1: Select exactly 5 random sounds for the quiz
    selected_sounds = list(LetterSound.objects.order_by('?')[:5])
    correct_letters = {sound.letter for sound in selected_sounds}

    # Step 2: Select additional letters to make the total choices 15
    all_letters = list(LetterSound.objects.exclude(pk__in=[s.pk for s in selected_sounds]))
    additional_choices = random.sample(all_letters, 15 - len(correct_letters))

    # Step 3: Combine correct and additional letters, then shuffle the list
    choices = selected_sounds + additional_choices
    random.shuffle(choices)

    # Pass the context to the template
    context = {
        'sounds': selected_sounds,
        'choices': choices,
        'correct_letters': list(correct_letters),
    }
    return render(request, 'letter_quiz.html', context)

# letter quiz end

# word matching start

def word_matching_view(request):
    words = list(WordAudio.objects.all())
    random.shuffle(words)
    selected_words = words[:4]

    # Shuffle the definitions for multiple-choice matching
    definitions = [word.definition for word in selected_words]
    random.shuffle(definitions)

    # Create correct pairs dictionary
    correct_pairs = {word.word: word.definition for word in selected_words}

    context = {
        'selected_words': selected_words,
        'definitions': definitions,
        'correct_pairs': correct_pairs,  # Pass correct pairs
    }
    return render(request, 'word_matching.html', context)

# word matching end

# word hunt start

def generate_grid(target_words):
    max_length = max(len(word.word) for word in target_words)
    grid_size = max(max_length + 2, 6) 

    grid = [['' for _ in range(grid_size)] for _ in range(grid_size)]

    # Place words either horizontally or vertically
    for word in target_words:
        placed = False
        while not placed:
            direction = random.choice(['horizontal', 'vertical'])
            if direction == 'horizontal':
                row = random.randint(0, grid_size - 1)
                col = random.randint(0, grid_size - len(word.word))
                if all(grid[row][col + i] == '' for i in range(len(word.word))):
                    for i in range(len(word.word)):
                        grid[row][col + i] = word.word[i]
                    placed = True
            else:  # Vertical placement
                row = random.randint(0, grid_size - len(word.word))
                col = random.randint(0, grid_size - 1)
                if all(grid[row + i][col] == '' for i in range(len(word.word))):
                    for i in range(len(word.word)):
                        grid[row + i][col] = word.word[i]
                    placed = True

    letter_sounds = [ls.letter for ls in LetterSound.objects.all()]

    # Fill empty spaces with random letters from LetterSound model
    for i in range(grid_size):
        for j in range(grid_size):
            if grid[i][j] == '':
                grid[i][j] = random.choice(letter_sounds)

    return grid, [word.word for word in target_words]

def word_hunt_view(request):
    target_words = random.sample(list(WordAudio.objects.all()), 3) 
    grid, placed_words = generate_grid(target_words)

    return render(request, 'word_hunt.html', {
        'grid': grid,
        'target_words': placed_words,
    })

# word hunt end

# word sequencing start

def word_sequencing_view(request):
    word_instance = random.choice(WordAudio.objects.all())
    word = word_instance.word
    shuffled_letters = list(word)
    random.shuffle(shuffled_letters) 

    context = {
        'original_word': word,
        'shuffled_letters': shuffled_letters,
    }
    return render(request, 'word_sequencing.html', context)

# word sequencing end

# word sound identification start

def word_sound_identification_view(request):
    all_words = WordAudio.objects.all()
    selected_word = random.choice(all_words) 

    correct_word = selected_word.word
    other_words = WordAudio.objects.exclude(word=correct_word)
    incorrect_choices = random.sample(list(other_words), 3)

    choices = [correct_word] + [word.word for word in incorrect_choices]
    random.shuffle(choices)

    context = {
        'selected_sound': selected_word,  # Use selected_word as selected_sound
        'choices': choices,
    }
    return render(request, 'word_sound_identification.html', context)

# word sound identification end

# word tracing start

def word_tracing_view(request):
    words = WordAudio.objects.all()
    selected_word = random.choice(words)

    context = {
        'selected_word': selected_word.word,
    }
    return render(request, 'word_tracing.html', context)

# word tracing end

# word formation (level 2) start

def word_formation_2_view(request):
    words = WordAudio.objects.all()
    selected_word = random.choice(words)  # Select a random word
    correct_word = selected_word.word
    scrambled = scramble_word(correct_word)  # Scramble the word, function defined in scrambled letters

    return render(request, 'word_formation_2.html', {
        'scrambled_word': scrambled,
        'correct_word': correct_word,
    })

# word formation (level 2) end

# word dictation start

def word_dictaition_view(request):
    word_sound = random.choice(WordAudio.objects.all())

    context = {
        'word_sound': word_sound,
    }
    return render(request, 'word_dictation.html', context)

# word dictation end

# word Charades 

def word_charades_view(request):
    word = random.choice(WordVideo.objects.all())
    context = {
        'video_url': word.video_file.url,
        'correct_word': word.word,
        'hint': word.hint
    }

    return render(request, 'word_charades.html', context)

# word charades

#tony
def letter_copy_view(request, pk=1):
    # Get the current video by primary key
    letter_video = get_object_or_404(LetterVideo, pk=pk)
    
    if request.method == 'POST':
        user_input = request.POST.get('letters').replace(' ', '').upper()
        correct_letters = letter_video.letter_set.replace(' ', '').upper()

        if user_input == correct_letters:
            feedback = "Well done! You've copied the letters correctly."

            # Find the next video (or loop back to the first if we're at the last)
            next_video = LetterVideo.objects.filter(pk__gt=letter_video.pk).first()
            if not next_video:  # If no more videos, restart from the first one
                next_video = LetterVideo.objects.first()
            
            # Redirect to the next video
            return redirect('letter_copy_with_pk', pk=next_video.pk)

        else:
            feedback = "Try again!"

        return render(request, 'letter_copy.html', {
            'letter_video': letter_video,
            'feedback': feedback
        })

    return render(request, 'letter_copy.html', {'letter_video': letter_video})

#tony
def match_and_write(request):
    letter_images = LetterImage.objects.all()
    total_letters = letter_images.count()

    # Initialize session variables if they don't exist
    if 'current_index' not in request.session:
        request.session['current_index'] = 0
        request.session['correct_answers'] = 0

    # Get the current index from the session
    current_index = request.session['current_index']
    feedback = ""

    # Check if there are letters to display
    if current_index < total_letters:
        current_letter_image = letter_images[current_index]
    else:
        feedback = "Congratulations! You've completed the activity!"
        return render(request, 'match_and_write.html', {
            'letter_image': None, 
            'feedback': feedback,
            'completed': True  # Indicate that the activity is completed
        })

    if request.method == "POST":
        answer = request.POST.get('answer', '').strip().upper()

        # Check the answer
        if answer == current_letter_image.letter:
            feedback = "Correct! Moving to the next letter."
            request.session['correct_answers'] += 1
            request.session['current_index'] += 1  # Move to the next letter
            request.session.modified = True  # Ensure session changes are saved
            return redirect('match_and_write')  # Redirect to the same view to refresh

        else:
            feedback = "Incorrect! Try again."

    return render(request, 'match_and_write.html', {
        'letter_image': current_letter_image,
        'feedback': feedback,
        'completed': False  # Indicate that the activity is not completed
    })

def reset_activity(request):
    # Clear the session data
    request.session.pop('current_index', None)
    request.session.pop('correct_answers', None)
    return redirect('match_and_write')  # Redirect to the match_and_write view

#tony
def letter_memory_game(request):
    # Initialize game session
    if 'score' not in request.session:
        request.session['score'] = 0
        request.session['rounds'] = 0
    
    # Fetch all LetterSounds
    letter_sounds = list(LetterSound.objects.all())

    if request.method == 'POST':
        user_answer = request.POST.get('user_answer')
        correct_letter = request.POST.get('correct_letter')

        if user_answer and user_answer.lower() == correct_letter.lower():
            request.session['score'] += 1
        request.session['rounds'] += 1

        # Check if the game should end
        if request.session['rounds'] >= 5:  # Play 5 rounds
            score = request.session['score']
            request.session.flush()  # Reset the session
            return render(request, 'game_over.html', {'score': score})

        # Select a random letter
        current_sound = random.choice(letter_sounds)
        return render(request, 'letter_memory_game.html', {
            'letter_sound': current_sound,
            'score': request.session['score'],
            'rounds': request.session['rounds'],
        })

    # Select a random letter on the first visit
    current_sound = random.choice(letter_sounds)
    return render(request, 'letter_memory_game.html', {
        'letter_sound': current_sound,
        'score': request.session['score'],
        'rounds': request.session['rounds'],
    })

#tony
def sound_sorting(request):
    # Get a random selection of 5 sounds from the LetterSound model
    sounds = list(LetterSound.objects.all())
    selected_sounds = random.sample(sounds, min(5, len(sounds)))

    if request.method == 'POST':
        user_answer = request.POST.get('user_answer')
        correct_sequence = ''.join(sound.letter for sound in selected_sounds)

        if user_answer.strip().upper() == correct_sequence:
            feedback = "Correct! Well done!"
        else:
            feedback = f"Wrong! The correct sequence was: {correct_sequence}"

        # Redirect to the same page to get new sounds
        return redirect('sound_sorting')

    return render(request, 'sound_sorting.html', {
        'selected_sounds': selected_sounds,
        'feedback': feedback if 'feedback' in locals() else None,
    })

#tony
def letter_sound_identification(request):
    # Get all letter sounds and images
    letter_sounds = LetterSound.objects.all()
    letter_images = LetterImage.objects.all()

    if request.method == 'POST':
        user_answer = request.POST.get('user_answer')
        correct_letter = request.POST.get('correct_letter')

        # Check if the answer is correct
        if user_answer.lower() == correct_letter.lower():
            feedback = "Correct!"
            # Optionally, you can increase score or round here
        else:
            feedback = f"Wrong! The correct letter was: {correct_letter}"

        # Select a new random letter sound and image
        letter_sound = random.choice(letter_sounds)
        letter_image = random.choice(letter_images)

        return render(request, 'your_template.html', {
            'letter_sound': letter_sound,
            'letter_image': letter_image,
            'feedback': feedback,
        })

    # On initial load, select a random letter sound and image
    letter_sound = random.choice(letter_sounds)
    letter_image = random.choice(letter_images)

    return render(request, 'letter_sound_identification.html', {
        'letter_sound': letter_sound,
        'letter_image': letter_image,
        'feedback': None,  # Start with no feedback
    })

#tony
def sound_imitation(request):
    letter_sounds = LetterSound.objects.all()
    letter_sound = random.choice(letter_sounds)

    return render(request, 'sound_imitation.html', {
        'letter_sound': letter_sound,
    })

# speaking charades in speaking start

@login_required
def speaking_charades_view(request):
    if request.method == 'POST':
        content_type_id = request.POST.get('content_type')
        object_id = request.POST.get('object_id')

        try:
            content_type = ContentType.objects.get(id=content_type_id)
            question = content_type.get_object_for_this_type(id=object_id)
        except (ContentType.DoesNotExist, question.model.DoesNotExist):
            return render(request, 'feedback.html', {'feedback': 'Invalid question!'})

        # Handle form submission
        form = WordCharadeForm(request.POST, request.FILES)
        if form.is_valid():
            word_charade = form.save(commit=False)
            word_charade.user = request.user
            word_charade.content_type = content_type
            word_charade.object_id = object_id
            word_charade.save()

            return render(request, 'feedback.html', {'feedback': 'Recording submitted successfully!'})

    else:
        content_type, question = random.choice([
            (ContentType.objects.get_for_model(WordVideo), WordVideo.objects.order_by('?').first()),
            (ContentType.objects.get_for_model(LetterImage), LetterImage.objects.order_by('?').first()),
        ])

        if not question:
            return render(request, 'feedback.html', {'feedback': 'No content available.'})

    return render(request, 'speaking_charades.html', {
        'question': question,
        'content_type_id': content_type.id,
        'object_id': question.id,
    })

# speaking charades in speaking end

# word countdown start

@login_required
def word_countdown_view(request):
    if request.method == 'GET':
        letter = random.choice(LetterImage.objects.all())
    else:
        letter_id = request.POST.get('letter_id')
        letter = get_object_or_404(LetterImage, id=letter_id)

        audio_file = request.FILES['audio_file']
        WordCountdownRecording.objects.create(
            user=request.user,
            letter=letter,
            audio_file=audio_file,
            submission_date=now()
        )
        return redirect('feedback')  

    return render(request, 'word_countdown.html', {'letter': letter})

@login_required
def feedback_view(request):
    recording = WordCountdownRecording.objects.filter(user=request.user).latest('submission_date')

    return render(request, 'feedback.html', {'recording': recording})


# word countdown end

# word sound discrimination start

def word_sound_discrimination_view(request):
    word_sounds = list(WordAudio.objects.all())

    if len(word_sounds) < 4:
        return render(request, 'error.html', {'message': 'Not enough sounds to play the game.'})

    odd_sound = random.choice(word_sounds)
    other_sounds = [s for s in word_sounds if s.word != odd_sound.word]

    identical_sound = random.choice(other_sounds)
    game_sounds = [identical_sound.audio_file.url] * 3 + [odd_sound.audio_file.url]
    random.shuffle(game_sounds)

    game_data = {
        "sounds": game_sounds,
        "correct": odd_sound.audio_file.url,
        "odd": odd_sound.word,
        "others": identical_sound.word,
    }

    return render(request, 'word_sound_discrimination.html', {'game_data': game_data})

# word sound discrimination end

# word sound memory start

def word_sound_memory_view(request):
    word_sounds = list(WordAudio.objects.all())
    selected_sounds = random.sample(word_sounds, 5)  # 5 pairs (10 cards)
    card_data = selected_sounds * 2  # Duplicate for matching pairs
    random.shuffle(card_data)  # Shuffle cards

    return render(request, 'word_sound_memory.html', {'card_data': card_data})

# word sound memory end

# listen and identify start

def listen_and_identify_view(request):
    all_sounds = WordAudio.objects.all()
    selected_sound = random.choice(all_sounds)

    correct_audio = selected_sound
    other_sounds = WordAudio.objects.exclude(word=correct_audio.word)
    incorrect_choices = random.sample(list(other_sounds), 3)

    choices = [correct_audio] + incorrect_choices
    random.shuffle(choices)

    context = {
        'selected_word': correct_audio.word,
        'correct_audio_id': correct_audio.id,  
        'choices': choices,
    }
    return render(request, 'listen_and_identify.html', context)

# listen and identify end

# word sound sequencing start

def word_sound_sequencing_view(request):
    word_audios = list(WordAudio.objects.all())
    if len(word_audios) < 4:
        raise ValueError("Not enough words in the database to play the game.")

    random.shuffle(word_audios)  
    selected_audios = word_audios[:4]

    shuffled_words = selected_audios[:]
    random.shuffle(shuffled_words)

    return render(request, 'word_sound_sequencing.html', {
        'audios': selected_audios,
        'shuffled_words': shuffled_words,
    })

# word sound sequencing end

# sentence matching start

def sentence_matching_view(request):
    all_sentences = Sentence.objects.all()
    selected_sentence = random.choice(all_sentences) 

    correct_definition = selected_sentence.definition
    other_definitions = Sentence.objects.exclude(definition=correct_definition)
    incorrect_choices = random.sample(list(other_definitions), 3)

    choices = [correct_definition] + [sentence.definition for sentence in incorrect_choices]
    random.shuffle(choices)

    context = {
        'selected_sentence': selected_sentence, 
        'choices': choices,
    }
    return render(request, 'sentence_matching.html', context)

# sentence matching end

# sentence hunt start

def sentence_hunt_view(request):
    sentences = list(Sentence.objects.filter(is_active=True))  
    selected_sentences = random.sample(sentences, min(3, len(sentences)))

    words = []
    for sentence in selected_sentences:
        words.extend(sentence.sentence.split())

    random.shuffle(words)

    grid_size = max(len(sentence.sentence.split()) for sentence in selected_sentences)
    
    context = {
        'grid_size': grid_size,
        'words': words,
        'selected_sentences': selected_sentences,
    }
    return render(request, 'sentence_hunt.html', context)

# sentence hunt end

# passage analysis start

def passage_analysis_view(request):
    paragraphs = Passage.objects.all()
    selected_paragraph = random.choice(paragraphs) 

    correct = selected_paragraph.main_idea

    choices = [correct] + selected_paragraph.wrong_choices
    random.shuffle(choices)

    context = {
        'selected_paragraph': selected_paragraph, 
        'choices': choices,
    }
    return render(request, 'passage_analysis.html', context)

# passage analysis end

# photo to word

def photo_to_word_view(request):
    question = WordAudio.objects.filter(image__isnull=False).order_by('?').first()

    incorrect_choices = WordAudio.objects.exclude(id=question.id).order_by('?')[:3]

    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)

    question_data = {
        'image_url': question.image.url,
        'choices': [choice.word for choice in choices],
        'correct_answer': question.word,
        'definition': question.definition
    }

    return render(request, 'photo_to_word.html', question_data)

# photo to word end

# word to photo 

def word_to_photo_view(request):
    question = WordAudio.objects.all().order_by('?').first()

    incorrect_choices = WordAudio.objects.exclude(id=question.id).order_by('?')[:3]

    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)

    question_data = {
        'word': question.word,
        'choices': [choice.image.url for choice in choices],
        'correct_answer': question.image.url,
        'definition': question.definition
    }

    return render(request, 'word_to_photo.html', question_data)

# word to photo

# video to word

def video_to_word_view(request):
    question = WordVideo.objects.order_by('?').first()

    incorrect_choices = WordVideo.objects.exclude(id=question.id).order_by('?')[:3]

    choices = list(incorrect_choices) + [question]
    random.shuffle(choices)

    context = {
        'video_url': question.video_file.url,
        'choices': [choice.word for choice in choices],
        'correct_answer': question.word,
        'hint': question.hint
    }

    return render(request, 'video_to_word.html', context)

# video to word end

# Sentence Synonym 

def sentence_synonym_view(request):
    question = SentenceSynonym.objects.order_by('?').first()

    distractors = list(SentenceSynonym.objects.exclude(id=question.id).values_list('correct_word', flat=True).order_by('?')[:3])

    choices = distractors + [question.correct_word]
    random.shuffle(choices)

    context = {
        'sentence': question.sentence,
        'choices': choices,
        'correct_answer': question.correct_word,
        'hint': question.hint
    }
    
    return render(request, 'sentence_synonym.html', context)

# Sentence synonym end

# Sentence punctuation

def sentence_punctuation_view(request):
    sentence = SentencePunctuation.objects.order_by('?').first()
    
    punctuation_choices = sentence.choices.split(",")
    random.shuffle(punctuation_choices) 

    correct = sentence.correct_answer
    context = {
        'sentence': sentence.text,
        'correct_text': sentence.correct_text,
        'choices': punctuation_choices,
        'correct_answer': sentence.correct_answer,
    }
    
    return render(request, 'sentence_punctuation.html', context)

# sentence punctuation end

# Paragraph creation 

def paragraph_creation_view(request):
    game = ParagraphCreation.objects.order_by('?').first()

    # Shuffle the sentences for display
    shuffled_sentences = game.sentences.copy()
    random.shuffle(shuffled_sentences)

    context = {
        'game': game,
        'shuffled_sentences': shuffled_sentences,
        'correct_order': game.correct_order,
    }

    return render(request, 'paragraph_creation.html', context)

# paragraph creation end

# find family

def find_family_view(request):
    all_families = AmharicLetterFamily.objects.all()
   
    selected_family = random.choice(all_families)
    letter = selected_family.letter
    correct_family = selected_family.family
    
    correct_members = random.sample(correct_family, 4)
    
    incorrect_families = random.sample([fam for fam in all_families if fam != selected_family], 2)
    incorrect_members = []
    for fam in incorrect_families:
        incorrect_members.extend(random.sample(fam.family, 2)) 
    
    mixed_options = correct_members + incorrect_members
    
    if len(mixed_options) > 10:
        mixed_options = mixed_options[:10]
    else:
        remaining_choices = 10 - len(mixed_options)
        additional_incorrect_members = []
        while len(additional_incorrect_members) < remaining_choices:
            incorrect_family = random.choice([fam for fam in all_families if fam != selected_family])
            additional_incorrect_members.extend(random.sample(incorrect_family.family, 1)) 
        
        mixed_options.extend(additional_incorrect_members)
    
    random.shuffle(mixed_options)

    context = {
        'letter': letter,
        'options': mixed_options,
        'correct_family': json.dumps(correct_family) 
    }
    
    return render(request, 'find_family.html', context)

# find family 

# arrange family

def arrange_family_view(request):
    letter_family = AmharicLetterFamily.objects.order_by('?').first()
    correct_family = letter_family.family  # This is the ordered family list
    
    # Shuffle the family members to create options
    options = correct_family[:]
    random.shuffle(options)

    context = {
        'question_type': 'arrange_family',
        'letter': letter_family.letter,
        'correct_family': correct_family,
        'options': options
    }
    return render(request, 'arrange_family.html', context)

# arrange family end

# find family 2

def find_family_2_view(request):
    letter_family = random.choice(AmharicLetterFamily.objects.all())
    correct_family_audios = letter_family.letters.all()

    correct_audio_files = [audio.audio_file.url for audio in correct_family_audios]

    other_families = AmharicLetterAudio.objects.exclude(family=letter_family)
    distractor_audios = random.sample(list(other_families), 6) 
    distractor_audio_files = [audio.audio_file.url for audio in distractor_audios]

    all_audio_choices = correct_audio_files + distractor_audio_files
    random.shuffle(all_audio_choices)

    context = {
        'question_type': 'find_family_2',
        "letter": letter_family.letter,
        "correct_audio_files": correct_audio_files,
        "audio_choices": all_audio_choices
    }
    return render(request, 'find_family_2.html', context)

# find family 2 end

# time stamp

def time_stamp_view(request):
    letter_audio_files = list(AmharicLetterAudio.objects.all())

    correct_letter_audio = random.choice(letter_audio_files)
    
    audio_sequence = random.sample(letter_audio_files, 4) 
    audio_sequence.append(correct_letter_audio)  
   
    random.shuffle(audio_sequence)

    audio_sequence_data = [
        {
            'letter': audio.letter,
            'audio_file': audio.audio_file.url  # Assuming you want to send the URL
        }
        for audio in audio_sequence
    ]

    return render(request, 'time_stamp.html', {
        'correct_letter': correct_letter_audio.letter,
        'audio_sequence': audio_sequence_data,
    })

# time stamp end

# number to word

def number_to_word_view(request):
    amharic_number = ""
    number_name = ""
    number_input = request.GET.get("number")

    if number_input:
        number = int(number_input)

        # Check if this number is already in the database
        existing_conversion = NumberToWord.objects.filter(number=number).first()
        if existing_conversion:
            amharic_number = existing_conversion.amharic_number
            number_name = existing_conversion.number_name
        else:
            # Handle cases where the number is not found in the database
            amharic_number = "N/A"
            number_name = "Not available in the database"

    context = {
        "amharic_number": amharic_number,
        "number_name": number_name,
        "number_input": number_input,
    }
    return render(request, "number_to_word.html", context)

# number to word end

# amharic english matching

def amharic_english_matching_view(request):
    sentences = list(AmharicEnglishMatching.objects.all())
    random.shuffle(sentences)
    selected_sentences = sentences[:4]

    definitions = [word.amharic_sentence for word in selected_sentences]
    random.shuffle(definitions)

    correct_pairs = {word.english_sentence: word.amharic_sentence for word in selected_sentences}

    context = {
        'selected_sentences': selected_sentences,
        'definitions': definitions,
        'correct_pairs': correct_pairs,  # Pass correct pairs
    }
    return render(request, 'amharic_english_matching.html', context)

# amharic english matching end

# Games Page

GAMES = [
    # Reading Games
    {'title': 'Letter Bingo', 'description': 'A Little description about the game', 'url': 'letter-bingo', 'category': 'Reading', 'level': 'Beginner'},
    {'title': 'Letter Memory', 'description': 'A Little description about the game', 'url': 'letter-memory', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Letter Sequencing', 'description': 'A Little description about the game', 'url': 'letter-sequencing', 'category': 'Reading', 'level': 'Beginner'},
    {'title': 'Letter Fill in the Blanks', 'description': 'A Little description about the game', 'url': 'letter-fill-in-the-blanks', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Word Matching', 'description': 'A Little description about the game', 'url': 'word-matching', 'category': 'Reading', 'level': 'Advanced'},
    {'title': 'Word Sequencing', 'description': 'A Little description about the game', 'url': 'word-sequencing', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Photo to Word', 'description': 'A Little description about the game', 'url': 'photo-to-word', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Word to Photo', 'description': 'A Little description about the game', 'url': 'word-to-photo', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Video to Word', 'description': 'A Little description about the game', 'url': 'video-to-word', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Find Family', 'description': 'A Little description about the game', 'url': 'find-family', 'category': 'Reading', 'level': 'Beginner'},
    {'title': 'Arrange Family', 'description': 'A Little description about the game', 'url': 'arrange-family', 'category': 'Reading', 'level': 'Beginner'},
    {'title': 'Word Dictation', 'description': 'A Little description about the game', 'url': 'word-dictation', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Word Hunt', 'description': 'A Little description about the game', 'url': 'word-hunt', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Sentence Hunt', 'description': 'A Little description about the game', 'url': 'sentence-hunt', 'category': 'Reading', 'level': 'Basic'},
    {'title': 'Passage Analysis', 'description': 'A Little description about the game', 'url': 'passage-analysis', 'category': 'Reading', 'level': 'Pro'},
    {'title': 'Sentence Matching', 'description': 'A Little description about the game', 'url': 'sentence-matching', 'category': 'Reading', 'level': 'Basic'},
     {'title': 'Sentence Synonym', 'description': 'A Little description about the game', 'url': 'sentence-synonym', 'category': 'Reading', 'level': 'Advanced'},
    {'title': 'Amharic-English Matching', 'description': 'A Little description about the game', 'url': 'amharic-english-matching', 'category': 'Reading', 'level': 'Basic'},
    
    # Writing Games
    {'title': 'Word Formation', 'description': 'A Little description about the game', 'url': 'word-formation', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Scrambled Letters', 'description': 'A Little description about the game', 'url': 'scrambled-letters', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Timed Writing', 'description': 'A Little description about the game', 'url': 'timed-writing', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Paragraph Creation', 'description': 'A Little description about the game', 'url': 'paragraph-creation', 'category': 'Writing', 'level': 'Pro'},
    {'title': 'Sentence Punctuation', 'description': 'A Little description about the game', 'url': 'sentence-punctuation', 'category': 'Writing', 'level': 'Advanced'},
    {'title': 'Letter Copy', 'description': 'A Little description about the game', 'url': 'letter-copy', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Tracing Board', 'description': 'A Little description about the game', 'url': 'tracing-board', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Match and Write', 'description': 'A Little description about the game', 'url': 'match-and-write', 'category': 'Writing', 'level': 'Beginner'},
        #tony
    {'title': 'Remembering Game', 'description': 'Test your memory by recalling items and their positions.', 'url': 'remembering-game', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Descriptive Image Game', 'description': 'Describe the images displayed and learn new vocabulary.', 'url': 'descriptive-image-game', 'category': 'Writing', 'level': 'Basic'},
    {'title': 'Descriptive Sentence Game', 'description': 'Form sentences based on the images provided.', 'url': 'descriptive-sentence-game', 'category': 'Writing', 'level': 'Basic'},
    {'title': 'Word Copy Game', 'description': 'Improve your spelling and memory by copying words.', 'url': 'word-copy-game', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Fill in the Blank', 'description': 'Complete sentences by filling in the missing words.', 'url': 'fill-in-the-blank-game', 'category': 'Writing', 'level': 'Basic'},
    {'title': 'Number to Word', 'description': 'Convert numbers into their corresponding words.', 'url': 'number-to-word', 'category': 'Writing', 'level': 'Beginner'},
    {'title': 'Writing Practice', 'description': 'Hone your writing skills by practicing letter and word formation.', 'url': 'writing-practice', 'category': 'Writing', 'level': 'Basic'},
    {'title': 'Video Game', 'description': 'Watch educational videos and complete related activities.', 'url': 'video-game', 'category': 'Writing', 'level': 'Advanced'},
    # Listening Games
    {'title': 'Letter Sound Discrimination', 'description': 'A Little description about the game', 'url': 'letter-sound-discrimination', 'category': 'Listening', 'level': 'Beginner'},
    {'title': 'Letter Sound Memory', 'description': 'A Little description about the game', 'url': 'letter-sound-memory', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Letter Sound Charades', 'description': 'A Little description about the game', 'url': 'letter-sound-charades', 'category': 'Listening', 'level': 'Beginner'},
    {'title': 'Audio Recognition', 'description': 'A Little description about the game', 'url': 'audio-recognition', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Word Sound Identification', 'description': 'A Little description about the game', 'url': 'word-sound-identification', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Sound Sorting', 'description': 'A Little description about the game', 'url': 'sound-sorting', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Letter Sound Sequencing', 'description': 'A Little description about the game', 'url': 'letter-sound-sequencing', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Listen and Write', 'description': 'A Little description about the game', 'url': 'listen-and-write', 'category': 'Listening', 'level': 'Basic'},
    {'title': 'Listen and Identify', 'description': 'A Little description about the game', 'url': 'listen-and-identify', 'category': 'Listening', 'level': 'Beginner'},
    {'title': 'Time Stamp', 'description': 'A Little description about the game', 'url': 'time-stamp', 'category': 'Listening', 'level': 'Advanced'},
    {'title': 'Find Family 2', 'description': 'A Little description about the game', 'url': 'find-family-2', 'category': 'Listening', 'level': 'Advanced'},
    {'title': 'Letter Dictation', 'description': 'A Little description about the game', 'url': 'letter-dictation', 'category': 'Listening', 'level': 'Beginner'},
    {'title': 'Letter Memory Game', 'description': 'A Little description about the game', 'url': 'letter-memory-game', 'category': 'Listening', 'level': 'Advanced'},
    {'title': 'story-telling', 'description': 'A Little description about the game', 'url': 'story-telling', 'category': 'Listening', 'level': 'Pro'},

    # Speaking Games
    {'title': 'Word Charades', 'description': 'A Little description about the game', 'url': 'word-charades', 'category': 'Speaking', 'level': 'Advanced'},
    {'title': 'Speaking Charades', 'description': 'A Little description about the game', 'url': 'speaking-charades', 'category': 'Speaking', 'level': 'Advanced'},
    {'title': 'Word Countdown', 'description': 'A Little description about the game', 'url': 'word-countdown', 'category': 'Speaking', 'level': 'Basic'},
    #tony
    {'title': 'Word Audio Activity', 'description': 'Learn word pronunciation through audio activities.', 'url': 'word-audio-activity', 'category': 'Speaking', 'level': 'Beginner'},
    {'title': 'Paragraph Game', 'description': 'Develop your reading comprehension through paragraph challenges.', 'url': 'paragraph-game', 'category': 'Speaking', 'level': 'Advanced'},
    {'title': 'Record Voice', 'description': 'Record your voice for analysis and feedback.', 'url': 'record-voice', 'category': 'Speaking', 'level': 'Beginner'},

    
    # # Other (Miscellaneous)
    # {'title': 'Bingo Game', 'description': 'A Little description about the game', 'url': 'bingo-game', 'category': 'Other', 'level': 'Beginner'},
    # {'title': 'Letter Hunt', 'description': 'A Little description about the game', 'url': 'letter-hunt', 'category': 'Other', 'level': 'Beginner'},
    # {'title': 'Letter Puzzles', 'description': 'A Little description about the game', 'url': 'letter-puzzles', 'category': 'Other', 'level': 'Beginner'},
]


def games_page_view(request):
    # Get the current logged-in user's profile
    user_profile = UserProfile.objects.get(user=request.user)

    # Get the user's unlocked levels as Level instances
    unlocked_levels = UserLevelProgress.objects.filter(user=request.user, is_locked=False).values_list('level', flat=True)

    # Initialize structure for levels
    levels = {
        'Beginner': {'Reading': [], 'Writing': [], 'Listening': [], 'Speaking': []},
        'Basic': {'Reading': [], 'Writing': [], 'Listening': [], 'Speaking': []},
        'Advanced': {'Reading': [], 'Writing': [], 'Listening': [], 'Speaking': []},
        'Pro': {'Reading': [], 'Writing': [], 'Listening': [], 'Speaking': []},
    }

    # Populate the structure with games but only for unlocked levels
    for game in GAMES:
        level_name = game['level']
        category = game['category']

        # Fetch the actual Level instance corresponding to the level_name
        level_instance = Level.objects.filter(name=level_name).first()

        if level_instance and level_instance.id in unlocked_levels:  # Check if the level is unlocked for the user
            levels[level_name][category].append(game)

    # Render the page with the filtered levels and games
    return render(request, 'games_page.html', {'levels': levels})

# Games Page end

# Story telling 

def story_telling_view(request, story_id=None, part_number=1):
    if story_id is None:  # Show top 10 stories if no story_id is provided
        stories = Story.objects.all().order_by('?')[:10]  # Adjust sorting as needed
        return render(request, 'story_list.html', {'stories': stories})

    # Fetch the story and specific part
    story = get_object_or_404(Story, id=story_id)
    part = get_object_or_404(StoryPart, story=story, part_number=part_number)

    # Find the next part, if it exists
    next_part = StoryPart.objects.filter(story=story, part_number=part_number + 1).first()

    # Pass the questions with a flag for correct answers
    for question in part.questions.all():
        options = question.options
        random.shuffle(options)  # Shuffle the options list
        question.options = [
            {"option": option, "is_correct": option == question.correct_answer}
            for option in options
    ]


    if request.method == "POST":
        user_answers = {}
        for question in part.questions.all():
            user_answers[question.id] = request.POST.get(f"answer_{question.id}")

        results = {}
        for question_id, user_answer in user_answers.items():
            question = part.questions.get(id=question_id)
            correct_answer = question.correct_answer
            results[question_id] = {
                "question": question.question_text,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "correct": user_answer == correct_answer,
            }

        return JsonResponse({"results": results})

    return render(request, 'story_telling.html', {
        'story': story,
        'part': part,
        'next_part': next_part
    })

# Story telling end


##tony
def letter_hunt_view(request):
    context = {'target_letter': 'A'}
    return render(request, 'letter_hunt.html', context)

def letter_puzzles(request):
    return render(request, 'letter_puzzles.html')

def tracing_board(request):
    # Define a list of letters to choose from
    letters = ["አ", "ሰ", "መ", "ሐ", "ን"]
    selected_letter = random.choice(letters)  # Randomly select a letter

    return render(request, 'board.html', {'letter': selected_letter})

def letter_sound_identification(request):
    # Get a random letter sound from the database
    letter_sounds = LetterSound.objects.all()
    selected_letter = random.choice(letter_sounds)
    letter = selected_letter.letter
    
    # Get all sound choices (4 random sounds)
    sound_choices = list(LetterSound.objects.all())

    # Ensure the correct sound is included in the choices
    correct_sound = selected_letter.sound_field.url  # Get the URL of the correct sound

    # Add the correct sound and select 3 random sounds from the remaining
    sound_choices.remove(selected_letter)  # Remove the correct sound from the choices
    sound_choices = random.sample(sound_choices, 3) + [selected_letter]  # Include the correct sound
    random.shuffle(sound_choices)  # Shuffle to randomize position

    # Prepare the context
    context = {
        'letter': letter,
        'sound_choices': sound_choices,  # Pass the whole objects
        'correct_sound': correct_sound,
    }
    return render(request, 'letter_sound_identification.html', context)

def letter_dictation(request):
    # Fetch all letter sounds
    letter_sounds = LetterSound.objects.all()

    # Select a random letter sound for the dictation
    selected_sound = random.choice(letter_sounds)

    context = {
        'letter': selected_sound.letter,
        'sound_url': selected_sound.sound_field.url,
    }
    return render(request, 'letter_dictation.html', context)

def bingo_game(request):
    question = BingoQuestion.objects.order_by('?').first()  # Get a random question
    context = {'question': question}
    return render(request, 'letter_sound_bingo.html', context)

def check_answer(request):
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        item_id = request.POST.get('item_id')

        try:
            question = BingoQuestion.objects.get(id=question_id)
            is_correct = question.correct_item.id == int(item_id)

            return JsonResponse({'correct': is_correct})
        except BingoQuestion.DoesNotExist:
            return JsonResponse({'error': 'Question not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def letter_sound_sequencing(request):
    sequence = LetterSoundSequence.objects.first()  # Get the first sequence; modify as needed
    sounds = sequence.sounds.all() if sequence else []  # Fetch sounds for the sequence
    correct_order = sequence.correct_order.split(',') if sequence else []

    return render(request, 'letter_sound_sequencing.html', {
        'sounds': sounds,
        'correct_order': correct_order
    })

## tony end

##tony after 
def get_random_question():
    models = [
        {'model': LetterSound, 'answer_field': 'letter'},
        {'model': LetterImage, 'answer_field': 'letter'},
        {'model': LetterVideo, 'answer_field': 'letter_set'},
        {'model': WordAudio, 'answer_field': 'word'},
        {'model': WordVideo, 'answer_field': 'word'}
    ]
    chosen = random.choice(models)
    item = chosen['model'].objects.order_by('?').first()  # Fetch a random entry from the chosen model
    return {
        'type': chosen['model'].__name__,
        'content': item,
        'answer_field': chosen['answer_field']
    }

def remembering_game(request):
    if request.method == 'POST':
        user_answer = request.POST.get('answer').strip().lower()
        correct_answer = request.session.get('correct_answer', '').lower()

        if user_answer == correct_answer:
            response = {'message': 'Correct! Moving to next question.'}
        else:
            response = {'message': 'Wrong, try again.'}
            return JsonResponse(response)

        question = get_random_question()
        request.session['correct_answer'] = getattr(question['content'], question['answer_field']).lower()
        response['new_question'] = {
            'type': question['type'],
            'display_text': str(question['content']),
        }
        return JsonResponse(response)

    question = get_random_question()
    request.session['correct_answer'] = getattr(question['content'], question['answer_field']).lower()
    return render(request, 'remembering_game.html', {'question': question})


def descriptive_image_game(request):
    if request.method == 'POST':
        # Get the answer and question id from the form data
        user_answer = request.POST.get('answer', '').strip().lower()
        question_id = request.POST.get('question_id')

        try:
            question = DescriptiveImage.objects.get(id=question_id)
        except DescriptiveImage.DoesNotExist:
            return JsonResponse({'message': 'Error: Question not found.'})

        # Correct answer comparison (case-insensitive)
        correct_answer = question.correct_word.lower()

        # Check the user's answer
        if user_answer == correct_answer:
            # Get a new random question
            new_question = random.choice(DescriptiveImage.objects.exclude(id=question_id))
            return JsonResponse({
                'message': 'Correct! Here is the next question.',
                'is_correct': True,
                'new_question_image_url': new_question.image.url,
                'new_question_id': new_question.id
            })
        else:
            return JsonResponse({
                'message': 'Incorrect, please try again!',
                'is_correct': False,
                'new_question_image_url': None
            })

    # If it's a GET request, return the first question
    question = random.choice(DescriptiveImage.objects.all())
    return render(request, 'descriptive_image_game.html', {'question': question})

def descriptive_sentence_game(request):
    # Get a random question from the database
    question = random.choice(DescriptiveSentenceQuestion.objects.all())
    
    if request.method == 'POST':
        # Get the user's answer from the POST request
        user_answer = request.POST.get('answer', '').strip().lower()  # Normalize answer
        correct_answer = question.correct_sentence.strip().lower()  # Normalize correct answer
        
        is_correct = user_answer == correct_answer
        message = "Correct!" if is_correct else "Incorrect. Try again."
        
        response_data = {
            'message': message,
            'is_correct': is_correct,
        }

        if is_correct:
            # Provide new question and image URL if answer is correct
            new_question = random.choice(DescriptiveSentenceQuestion.objects.all())
            response_data['new_question_image_url'] = new_question.image.url
            response_data['new_question_id'] = new_question.id
        
        return JsonResponse(response_data)
    
    return render(request, 'descriptive_sentence_game.html', {'question': question})

def word_copy_game(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input')
        word_id = request.POST.get('word_id')
        word = WordAudio.objects.get(id=word_id)
        
        if user_input == word.word:
            # Fetch a new random word from the database
            new_word = random.choice(WordAudio.objects.exclude(id=word_id))
            return JsonResponse({
                'message': 'Correct!',
                'new_word': new_word.word,
                'new_word_id': new_word.id
            })
        else:
            return JsonResponse({'message': 'Try Again'})

    # Initial word for GET request
    word = random.choice(WordAudio.objects.all())
    return render(request, 'word_copy_game.html', {'word': word})


def fill_in_the_blank_game(request):
    if request.method == 'POST':
        user_answers = request.POST.getlist('user_answers[]')
        question_id = request.POST.get('question_id')
        question = FillInTheBlank.objects.get(id=question_id)
        
        correct_answers = [ans.strip() for ans in question.correct_answer.split(",")]
        is_correct = user_answers == correct_answers

        if is_correct:
            message = "Correct!"
            new_question = random.choice(FillInTheBlank.objects.exclude(id=question_id))
            split_question = new_question.question.split('__')  # Assuming blanks are represented by '__'
            return JsonResponse({
                'message': message,
                'split_question': split_question,
                'blanks': len(new_question.correct_answer.split(",")),
                'question_id': new_question.id
            })
        else:
            return JsonResponse({'message': 'Incorrect. Try again!'})

    # Initial GET request - select a random question
    question = random.choice(FillInTheBlank.objects.all())
    split_question = question.question.split('__')  # Assuming blanks are represented by '__'
    return render(request, 'fill_in_the_blank_game.html', {
        'question': question,
        'split_question': split_question,
        'blanks': len(question.correct_answer.split(","))
    })

def number_to_word_game(request):
    # If it's a POST request (form submission for checking answer)
    if request.method == 'POST':
        user_answer = request.POST.get('user_answer').strip().lower()
        number_id = request.POST.get('number_id')
        number = Numbers.objects.get(id=number_id)

        # Check if the user's answer matches the word representation
        if user_answer == number.word.lower():
            message = 'Correct!'
        else:
            message = 'Wrong answer. Try again!'

        # Return feedback message after checking answer
        return JsonResponse({
            'message': message,
            'number': number.number,
            'amharic_word': number.amharic_word,
        })

    # If it's a GET request, show a random number
    number = Numbers.objects.order_by('?').first()
    return render(request, 'number_to_word_game.html', {'number': number})

def writing_practice(request):
    if request.method == 'POST':
        form = WritingSubmissionForm(request.POST)
        if form.is_valid():
            form.instance.user = request.user
            submission = form.save()
            word_count = len(submission.content.split())
            feedback_message = f"Great job! You wrote {word_count} words."

            # Optionally, check if the text is too short
            if word_count < 10:
                feedback_message = "Try writing a bit more next time! A few more sentences would be great."

            return render(request, 'writing_practice_success.html', {'feedback_message': feedback_message})
    else:
        form = WritingSubmissionForm()

    return render(request, 'writing_practice.html', {'form': form})

def video_game(request, video_id=None):
    if video_id is None:
        video = Video.objects.first()  # Load the first video if no ID is provided
    else:
        video = get_object_or_404(Video, id=video_id)
    
    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
            return redirect('video_game', video_id=video.id)
    else:
        form = VideoForm()

    return render(request, 'video_game.html', {'form': form, 'video': video})

def submit_video_response(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == "POST":
        response = request.POST.get('response')
        if response:
            VideoResponse.objects.create(
                video=video,
                student=request.user,
                response=response
            )
            # Fetch the next video
            next_video = Video.objects.exclude(id=video.id).first()  # Get the next video
            if next_video:
                return redirect('video_game_with_id', video_id=next_video.id)  # Redirect to the next video
            else:
                return redirect('video_game')  # Redirect to video game page if no next video
    return render(request, 'video_game.html', {'video': video})




@login_required
def word_audio_activity(request):
    word_audio = WordAudio.objects.order_by('?').first()
    return render(request, 'word_audio_activity.html', {'word_audio': word_audio})

@login_required
def submit_word_audio_recording(request):
    if request.method == "POST":
        user = request.user
        word_audio_id = request.POST.get("word_audio_id")
        audio_data = request.POST.get("audio_data")  # Base64 encoded data

        word_audio = get_object_or_404(WordAudio, id=word_audio_id)

        # Decode and save the recording
        format, audio_str = audio_data.split(';base64,')
        ext = format.split('/')[1]
        audio_file = ContentFile(base64.b64decode(audio_str), name=f"user_{user.id}_word_{word_audio.id}.{ext}")

        recording = WordAudioRecording.objects.create(
            word_audio=word_audio,
            user=user,
            recording_file=audio_file
        )
        return JsonResponse({"message": "Recording uploaded successfully!"})
    return JsonResponse({"error": "Invalid request"}, status=400)


def sentence_audio_game(request, sentence_id):
    sentence = Sentence.objects.get(id=sentence_id)
    
    if request.method == 'POST' and request.FILES.get('audio_data'):
        audio_data = request.FILES['audio_data']
        # Save audio recording to the database or process it as needed
        # Example: create a new model to store the user recordings
        # UserRecording.objects.create(audio=audio_data, sentence=sentence, user=request.user)

        # Redirect or render a success message
        return JsonResponse({'message': 'Recording uploaded successfully!'})

    return render(request, 'sentence_game.html', {'sentence': sentence})

def paragraph_game(request):
    # Fetch a random active paragraph
    paragraph = Paragraph.objects.filter(is_active=True).order_by('?').first()
    
    # Return the paragraph content to the template
    return render(request, 'paragraph_game.html', {'paragraph': paragraph})

def record_voice(request):
    if request.method == 'POST':
        form = VoiceRecordingForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('voice_recording_success')  # Redirect to success page or display a success message
    else:
        form = VoiceRecordingForm()
    
    return render(request, 'record_voice.html', {'form': form})
def voice_recording_success(request):
    # You can add additional context here if needed
    return render(request, 'voice_recording_success.html')


### ----------- Multiple Choices Question ----------- 

def multiple_choice_view(request):
    questions = get_random_questions()
    return render(request, 'multiple_choice.html', {'questions': questions})


### --------- LeaderBoard ------------ 

def leaderboard_view(request):
    users = UserProfile.objects.filter(is_subscribed=True).order_by('-aura_points')

    # Assign ranks with ties
    ranked_users = []
    previous_points = None
    previous_rank = 0
    tied_count = 0

    for i, user in enumerate(users, start=1):
        if user.aura_points == previous_points:
            tied_count += 1
            rank = previous_rank
        else:
            rank = previous_rank + tied_count + 1
            tied_count = 0

        previous_points = user.aura_points
        previous_rank = rank

        ranked_users.append({
            "rank": rank,
            "full_name": user.full_name,
            "aura_points": user.aura_points
        })

    # Separate the top 3 and paginate the rest
    top_3 = ranked_users[:3]
    paginator = Paginator(ranked_users[3:], 7)
    page_number = request.GET.get('page')
    paginated_users = paginator.get_page(page_number)

    return render(request, 'leaderboard.html', {
        'top_3': top_3,
        'paginated_users': paginated_users,
    })


#tony custom admin
@staff_member_required
def custom_admin_page(request):
    # Fetch general stats
    profiles = UserProfile.objects.all()
    total_profiles = profiles.count()
    subscribed_profiles = profiles.filter(is_subscribed=True).count()

    context = {
        "total_profiles": total_profiles,
        "subscribed_profiles": subscribed_profiles,
    }

    return render(request, 'custom_admin.html', context)

@staff_member_required
def user_profiles(request):
    profiles = UserProfile.objects.all()
    user_point_history = {profile.id: PointHistory.objects.filter(user_profile=profile) for profile in profiles}
    
    context = {
        "profiles": profiles,
        "user_point_history": user_point_history, 
    }

    return render(request, 'user_profiles.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from .models import Event
from .forms import EventForm

# View to display all events and handle CRUD operations
@staff_member_required
def event_page(request):
    events = Event.objects.all()  # Get all events
    form = EventForm()

    if request.method == 'POST':
        # Handle event creation
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('events_page')  # Redirect to the event list page

    context = {
        'events': events,
        'form': form
    }
    return render(request, 'eventadmin.html', context)

# View to handle updating an event
@staff_member_required
def update_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    form = EventForm(instance=event)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('events_page')  # Redirect after saving

    context = {
        'form': form,
        'event': event
    }
    return render(request, 'eventadmin.html', context)

# View to handle deleting an event
@staff_member_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.delete()
        return redirect('events_page')  # Redirect after deletion
    return render(request, 'delete_event.html', {'event': event})

@staff_member_required
def letter_sound_admin(request):
    # Handle CREATE operation
    if request.method == 'POST' and 'create' in request.POST:
        form = LetterSoundForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('letter_sound_admin')
    
    # Handle UPDATE operation
    elif request.method == 'POST' and 'update' in request.POST:
        letter_sound = get_object_or_404(LetterSound, id=request.POST['id'])
        form = LetterSoundForm(request.POST, request.FILES, instance=letter_sound)
        if form.is_valid():
            form.save()
            return redirect('letter_sound_admin')
    
    # Handle DELETE operation
    elif request.method == 'POST' and 'delete' in request.POST:
        letter_sound = get_object_or_404(LetterSound, id=request.POST['id'])
        letter_sound.delete()
        return redirect('letter_sound_admin')

    # List all LetterSound objects
    letter_sounds = LetterSound.objects.all()
    form = LetterSoundForm()  # Empty form for creating new LetterSound
    return render(request, 'lettersound_admin.html', {'form': form, 'letter_sounds': letter_sounds})


# WordAudio CRUD Operations
@staff_member_required
def word_audio_admin(request):
    # Handle create, update, and delete logic
    if request.method == 'POST':
        if 'create' in request.POST:
            form = WordAudioForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
        elif 'update' in request.POST:
            word_audio_id = request.POST.get('id')
            word_audio = get_object_or_404(WordAudio, id=word_audio_id)
            form = WordAudioForm(request.POST, request.FILES, instance=word_audio)
            if form.is_valid():
                form.save()
        elif 'delete' in request.POST:
            word_audio_id = request.POST.get('id')
            word_audio = get_object_or_404(WordAudio, id=word_audio_id)
            word_audio.delete()

    # Get all WordAudio objects for displaying in the table
    word_audios = WordAudio.objects.all()

    # Render form for creation of new WordAudio
    form = WordAudioForm()

    return render(request, 'wordaudio-admin.html', {'form': form, 'word_audios': word_audios})
    
# WordVideo CRUD Operations
@staff_member_required
def word_video_admin(request):
    # Handling CREATE and UPDATE actions
    if request.method == "POST":
        word_video_id = request.POST.get("id")
        if word_video_id:  # Update an existing Word Video entry
            word_video = get_object_or_404(WordVideo, pk=word_video_id)
            form = WordVideoForm(request.POST, request.FILES, instance=word_video)
        else:  # Create a new Word Video entry
            form = WordVideoForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('word_video_admin')  # Redirect to the same page after saving
    
    else:
        form = WordVideoForm()

    # Handling DELETE action
    if request.method == "POST" and "delete" in request.POST:
        word_video_id = request.POST.get("id")
        if word_video_id:
            word_video = get_object_or_404(WordVideo, pk=word_video_id)
            word_video.delete()
            return redirect('wordvideo_admin')  # Redirect to the same page after deleting

    # Get all existing Word Video entries
    word_videos = WordVideo.objects.all()

    return render(request, 'wordvideo-admin.html', {
        'form': form,
        'word_videos': word_videos
    })

@staff_member_required
def letter_video_admin(request):
    if request.method == "POST" and "delete" in request.POST:
        video_id = request.POST.get("id")
        try:
            video = LetterVideo.objects.get(id=video_id)
            video.delete()
            # Optional: Add a success message here
        except LetterVideo.DoesNotExist:
            # Optional: Add an error message here
            pass
        return redirect("letter_video_admin")
    
    # Fetch all LetterVideos to display
    letter_videos = LetterVideo.objects.all()
    return render(request, "letter_video_admin.html", {"letter_videos": letter_videos})

@staff_member_required
def letter_image_admin(request):
    if request.method == "POST":
        id = request.POST.get("id")
        letter = request.POST.get("letter")
        image = request.FILES.get("image")

        if id:  # Update existing entry
            letter_image = LetterImage.objects.get(id=id)
            letter_image.letter = letter
            if image:
                letter_image.image = image
            letter_image.save()
            messages.success(request, "Letter Image updated successfully.")
        else:  # Create new entry
            LetterImage.objects.create(letter=letter, image=image)
            messages.success(request, "Letter Image added successfully.")
        
        return redirect("letter_image_admin")

    # Handle delete requests
    if "delete" in request.GET:
        id = request.GET.get("delete")
        letter_image = LetterImage.objects.get(id=id)
        letter_image.delete()
        messages.success(request, "Letter Image deleted successfully.")
        return redirect("letter_image_admin")

    # Display all entries
    letter_images = LetterImage.objects.all()
    return render(request, "letter_image_admin.html", {"letter_images": letter_images})


from .forms import WordCountdownRecordingForm

@staff_member_required
def admin_wordcountdown(request):
    # Query parameters
    action = request.GET.get('action', 'list')  # Default action is 'list'
    pk = request.GET.get('pk')

    # Fetch all recordings for the list view
    recordings = WordCountdownRecording.objects.all()

    # Initialize variables
    recording = None
    form = None

    # Handle actions
    if action == 'create' or (action == 'update' and pk):
        recording = get_object_or_404(WordCountdownRecording, pk=pk) if pk else None
        if request.method == "POST":
            form = WordCountdownRecordingForm(
                request.POST, request.FILES, instance=recording
            )
            if form.is_valid():
                form.save()
                return redirect('admin_wordcountdown')
            else:
                # Log the form errors to the console for debugging
                print(form.errors)  # Remove in production
        else:
            form = WordCountdownRecordingForm(instance=recording)
    
    elif action == 'delete' and pk:
        recording = get_object_or_404(WordCountdownRecording, pk=pk)
        if request.method == "POST":
            recording.delete()
            return redirect('admin_wordcountdown')

    # Render the unified template
    return render(request, 'admin_wordcountdown.html', {
        'recordings': recordings,
        'form': form,
        'action': action,
        'recording': recording,
    })


from .forms import SentenceForm

def sentence_customadmin(request):
    sentences = Sentence.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = SentenceForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('sentence_customadmin')
        elif 'update' in request.POST:
            sentence_id = request.POST.get('sentence_id')
            sentence = get_object_or_404(Sentence, pk=sentence_id)
            form = SentenceForm(request.POST, instance=sentence)
            if form.is_valid():
                form.save()
                return redirect('sentence_customadmin')
        elif 'delete' in request.POST:
            sentence_id = request.POST.get('sentence_id')
            sentence = get_object_or_404(Sentence, pk=sentence_id)
            sentence.delete()
            return redirect('sentence_customadmin')
    
    form = SentenceForm()  # For creating a new sentence
    return render(request, 'sentence_customadmin.html', {
        'sentences': sentences,
        'form': form,
    })



from .forms import PassageForm

def passage_customadmin(request):
    passages = Passage.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = PassageForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('passage_customadmin')
        
        elif 'update' in request.POST:
            passage_id = request.POST.get('passage_id')
            passage = get_object_or_404(Passage, pk=passage_id)
            form = PassageForm(request.POST, instance=passage)
            if form.is_valid():
                form.save()
                return redirect('passage_customadmin')
            else:
                print(form.errors)  # Debugging line to see form errors
        
        elif 'delete' in request.POST:
            passage_id = request.POST.get('passage_id')
            passage = get_object_or_404(Passage, pk=passage_id)
            passage.delete()
            return redirect('passage_customadmin')
    
    form = PassageForm()  # For creating a new passage
    return render(request, 'passage_customadmin.html', {
        'passages': passages,
        'form': form,
    })



from .forms import DescriptiveImageForm, DescriptiveSentenceQuestionForm

def descriptive_image_customadmin(request):
    images = DescriptiveImage.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = DescriptiveImageForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('descriptive_image_customadmin')
        
        elif 'update' in request.POST:
            image_id = request.POST.get('image_id')
            image = get_object_or_404(DescriptiveImage, pk=image_id)
            form = DescriptiveImageForm(request.POST, request.FILES, instance=image)
            if form.is_valid():
                form.save()
                return redirect('descriptive_image_customadmin')
        
        elif 'delete' in request.POST:
            image_id = request.POST.get('image_id')
            image = get_object_or_404(DescriptiveImage, pk=image_id)
            image.delete()
            return redirect('descriptive_image_customadmin')
    
    form = DescriptiveImageForm()
    return render(request, 'descriptive_image_customadmin.html', {
        'images': images,
        'form': form,
    })

def descriptive_sentence_question_customadmin(request):
    questions = DescriptiveSentenceQuestion.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = DescriptiveSentenceQuestionForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('descriptive_sentence_question_customadmin')
        
        elif 'update' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(DescriptiveSentenceQuestion, pk=question_id)
            form = DescriptiveSentenceQuestionForm(request.POST, request.FILES, instance=question)
            if form.is_valid():
                form.save()
                return redirect('descriptive_sentence_question_customadmin')
        
        elif 'delete' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(DescriptiveSentenceQuestion, pk=question_id)
            question.delete()
            return redirect('descriptive_sentence_question_customadmin')
    
    form = DescriptiveSentenceQuestionForm()
    return render(request, 'descriptive_sentence_question_customadmin.html', {
        'questions': questions,
        'form': form,
    })


from .forms import FillInTheBlankForm, NumbersForm

def fill_in_the_blank_customadmin(request):
    questions = FillInTheBlank.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = FillInTheBlankForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('fill_in_the_blank_customadmin')
        
        elif 'update' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(FillInTheBlank, pk=question_id)
            form = FillInTheBlankForm(request.POST, instance=question)
            if form.is_valid():
                form.save()
                return redirect('fill_in_the_blank_customadmin')
        
        elif 'delete' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(FillInTheBlank, pk=question_id)
            question.delete()
            return redirect('fill_in_the_blank_customadmin')
    
    form = FillInTheBlankForm()
    return render(request, 'fill_in_the_blank_customadmin.html', {
        'questions': questions,
        'form': form,
    })

def numbers_customadmin(request):
    numbers_list = Numbers.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = NumbersForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('numbers_customadmin')
        
        elif 'update' in request.POST:
            number_id = request.POST.get('number_id')
            number = get_object_or_404(Numbers, pk=number_id)
            form = NumbersForm(request.POST, instance=number)
            if form.is_valid():
                form.save()
                return redirect('numbers_customadmin')
        
        elif 'delete' in request.POST:
            number_id = request.POST.get('number_id')
            number = get_object_or_404(Numbers, pk=number_id)
            number.delete()
            return redirect('numbers_customadmin')
    
    form = NumbersForm()
    return render(request, 'numbers_customadmin.html', {
        'numbers': numbers_list,
        'form': form,
    })


from .models import WritingSubmission
from .forms import WritingSubmissionForm

def writing_submission_customadmin(request):
    submissions = WritingSubmission.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = WritingSubmissionForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('writing_submission_customadmin')
        
        elif 'update' in request.POST:
            submission_id = request.POST.get('submission_id')
            submission = get_object_or_404(WritingSubmission, pk=submission_id)
            form = WritingSubmissionForm(request.POST, instance=submission)
            if form.is_valid():
                form.save()
                return redirect('writing_submission_customadmin')
        
        elif 'delete' in request.POST:
            submission_id = request.POST.get('submission_id')
            submission = get_object_or_404(WritingSubmission, pk=submission_id)
            submission.delete()
            return redirect('writing_submission_customadmin')
    
    form = WritingSubmissionForm()
    return render(request, 'writing_submission_customadmin.html', {
        'submissions': submissions,
        'form': form,
    })


from .forms import VideoForm

def video_customadmin(request):
    videos = Video.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = VideoForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('video_customadmin')
        
        elif 'update' in request.POST:
            video_id = request.POST.get('video_id')
            video = get_object_or_404(Video, pk=video_id)
            form = VideoForm(request.POST, request.FILES, instance=video)
            if form.is_valid():
                form.save()
                return redirect('video_customadmin')
        
        elif 'delete' in request.POST:
            video_id = request.POST.get('video_id')
            video = get_object_or_404(Video, pk=video_id)
            video.delete()
            return redirect('video_customadmin')
    
    form = VideoForm()
    return render(request, 'video_customadmin.html', {
        'videos': videos,
        'form': form,
    })


from .forms import VideoResponseForm, WordAudioRecordingForm

def video_response_customadmin(request):
    responses = VideoResponse.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = VideoResponseForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('video_response_customadmin')
        
        elif 'update' in request.POST:
            response_id = request.POST.get('response_id')
            response = get_object_or_404(VideoResponse, pk=response_id)
            form = VideoResponseForm(request.POST, instance=response)
            if form.is_valid():
                form.save()
                return redirect('video_response_customadmin')
        
        elif 'delete' in request.POST:
            response_id = request.POST.get('response_id')
            response = get_object_or_404(VideoResponse, pk=response_id)
            response.delete()
            return redirect('video_response_customadmin')
    
    form = VideoResponseForm()
    videos = Video.objects.all()  # For the dropdown
    return render(request, 'video_response_customadmin.html', {
        'responses': responses,
        'form': form,
        'videos': videos,
    })

def word_audio_recording_customadmin(request):
    recordings = WordAudioRecording.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = WordAudioRecordingForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('word_audio_recording_customadmin')
        
        elif 'update' in request.POST:
            recording_id = request.POST.get('recording_id')
            recording = get_object_or_404(WordAudioRecording, pk=recording_id)
            form = WordAudioRecordingForm(request.POST, request.FILES, instance=recording)
            if form.is_valid():
                form.save()
                return redirect('word_audio_recording_customadmin')
        
        elif 'delete' in request.POST:
            recording_id = request.POST.get('recording_id')
            recording = get_object_or_404(WordAudioRecording, pk=recording_id)
            recording.delete()
            return redirect('word_audio_recording_customadmin')
    
    form = WordAudioRecordingForm()
    word_audios = WordAudio.objects.all()  # For the dropdown
    return render(request, 'word_audio_recording_customadmin.html', {
        'recordings': recordings,
        'form': form,
        'word_audios': word_audios,
    })


from .models import Paragraph, VoiceRecording
from .forms import ParagraphForm, VoiceRecordingForm

def paragraph_customadmin(request):
    paragraphs = Paragraph.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = ParagraphForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('paragraph_customadmin')
        
        elif 'update' in request.POST:
            paragraph_id = request.POST.get('paragraph_id')
            paragraph = get_object_or_404(Paragraph, pk=paragraph_id)
            form = ParagraphForm(request.POST, instance=paragraph)
            if form.is_valid():
                form.save()
                return redirect('paragraph_customadmin')
        
        elif 'delete' in request.POST:
            paragraph_id = request.POST.get('paragraph_id')
            paragraph = get_object_or_404(Paragraph, pk=paragraph_id)
            paragraph.delete()
            return redirect('paragraph_customadmin')
    
    form = ParagraphForm()
    return render(request, 'paragraph_customadmin.html', {
        'paragraphs': paragraphs,
        'form': form,
    })

def voice_recording_customadmin(request):
    recordings = VoiceRecording.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = VoiceRecordingForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('voice_recording_customadmin')
        
        elif 'update' in request.POST:
            recording_id = request.POST.get('recording_id')
            recording = get_object_or_404(VoiceRecording, pk=recording_id)
            form = VoiceRecordingForm(request.POST, request.FILES, instance=recording)
            if form.is_valid():
                form.save()
                return redirect('voice_recording_customadmin')
        
        elif 'delete' in request.POST:
            recording_id = request.POST.get('recording_id')
            recording = get_object_or_404(VoiceRecording, pk=recording_id)
            recording.delete()
            return redirect('voice_recording_customadmin')
    
    form = VoiceRecordingForm()
    return render(request, 'voice_recording_customadmin.html', {
        'recordings': recordings,
        'form': form,
    })


from .forms import ParagraphCreationForm

def paragraph_creation_customadmin(request):
    paragraphs = ParagraphCreation.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = ParagraphCreationForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('paragraph_creation_customadmin')
        
        elif 'update' in request.POST:
            paragraph_id = request.POST.get('paragraph_id')
            paragraph = get_object_or_404(ParagraphCreation, pk=paragraph_id)
            form = ParagraphCreationForm(request.POST, instance=paragraph)
            if form.is_valid():
                form.save()
                return redirect('paragraph_creation_customadmin')
        
        elif 'delete' in request.POST:
            paragraph_id = request.POST.get('paragraph_id')
            paragraph = get_object_or_404(ParagraphCreation, pk=paragraph_id)
            paragraph.delete()
            return redirect('paragraph_creation_customadmin')
    
    form = ParagraphCreationForm()
    return render(request, 'paragraph_creation_customadmin.html', {
        'paragraphs': paragraphs,
        'form': form,
    })


from .forms import AmharicLetterFamilyForm, AmharicLetterAudioForm

def amharic_letter_family_customadmin(request):
    families = AmharicLetterFamily.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = AmharicLetterFamilyForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('amharic_letter_family_customadmin')
        
        elif 'update' in request.POST:
            family_id = request.POST.get('family_id')
            family = get_object_or_404(AmharicLetterFamily, pk=family_id)
            form = AmharicLetterFamilyForm(request.POST, instance=family)
            if form.is_valid():
                form.save()
                return redirect('amharic_letter_family_customadmin')
        
        elif 'delete' in request.POST:
            family_id = request.POST.get('family_id')
            family = get_object_or_404(AmharicLetterFamily, pk=family_id)
            family.delete()
            return redirect('amharic_letter_family_customadmin')
    
    form = AmharicLetterFamilyForm()
    return render(request, 'amharic_letter_family_customadmin.html', {
        'families': families,
        'form': form,
    })

def amharic_letter_audio_customadmin(request):
    audios = AmharicLetterAudio.objects.all()
    
    if request.method == 'POST':
        if 'create' in request.POST:
            form = AmharicLetterAudioForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('amharic_letter_audio_customadmin')
        
        elif 'update' in request.POST:
            audio_id = request.POST.get('audio_id')
            audio = get_object_or_404(AmharicLetterAudio, pk=audio_id)
            form = AmharicLetterAudioForm(request.POST, request.FILES, instance=audio)
            if form.is_valid():
                form.save()
                return redirect('amharic_letter_audio_customadmin')
        
        elif 'delete' in request.POST:
            audio_id = request.POST.get('audio_id')
            audio = get_object_or_404(AmharicLetterAudio, pk=audio_id)
            audio.delete()
            return redirect('amharic_letter_audio_customadmin')
    
    form = AmharicLetterAudioForm()
    families = AmharicLetterFamily.objects.all()  # For the dropdown
    return render(request, 'amharic_letter_audio_customadmin.html', {
        'audios': audios,
        'form': form,
        'families': families,
    })


from .forms import LetterFillInForm, NumberToWordForm

def letter_fill_in_customadmin(request):
    letters = LetterFillIn.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = LetterFillInForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('letter_fill_in_customadmin')
        
        elif 'update' in request.POST:
            letter_id = request.POST.get('letter_id')
            letter = get_object_or_404(LetterFillIn, pk=letter_id)
            form = LetterFillInForm(request.POST, instance=letter)
            if form.is_valid():
                form.save()
                return redirect('letter_fill_in_customadmin')
        
        elif 'delete' in request.POST:
            letter_id = request.POST.get('letter_id')
            letter = get_object_or_404(LetterFillIn, pk=letter_id)
            letter.delete()
            return redirect('letter_fill_in_customadmin')

    form = LetterFillInForm()
    return render(request, 'letter_fill_in_customadmin.html', {
        'letters': letters,
        'form': form,
    })

def number_to_word_customadmin(request):
    numbers = NumberToWord.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = NumberToWordForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('number_to_word_customadmin')
        
        elif 'update' in request.POST:
            number_id = request.POST.get('number_id')
            number = get_object_or_404(NumberToWord, pk=number_id)
            form = NumberToWordForm(request.POST, instance=number)
            if form.is_valid():
                form.save()
                return redirect('number_to_word_customadmin')
        
        elif 'delete' in request.POST:
            number_id = request.POST.get('number_id')
            number = get_object_or_404(NumberToWord, pk=number_id)
            number.delete()
            return redirect('number_to_word_customadmin')

    form = NumberToWordForm()
    return render(request, 'number_to_word_customadmin.html', {
        'numbers': numbers,
        'form': form,
    })


from .forms import AmharicEnglishMatchingForm, SentenceSynonymForm

def amharic_english_matching_customadmin(request):
    matches = AmharicEnglishMatching.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = AmharicEnglishMatchingForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('amharic_english_matching_customadmin')
        
        elif 'update' in request.POST:
            match_id = request.POST.get('match_id')
            match = get_object_or_404(AmharicEnglishMatching, pk=match_id)
            form = AmharicEnglishMatchingForm(request.POST, instance=match)
            if form.is_valid():
                form.save()
                return redirect('amharic_english_matching_customadmin')
        
        elif 'delete' in request.POST:
            match_id = request.POST.get('match_id')
            match = get_object_or_404(AmharicEnglishMatching, pk=match_id)
            match.delete()
            return redirect('amharic_english_matching_customadmin')

    form = AmharicEnglishMatchingForm()
    return render(request, 'amharic_english_matching_customadmin.html', {
        'matches': matches,
        'form': form,
    })

def sentence_synonym_customadmin(request):
    synonyms = SentenceSynonym.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = SentenceSynonymForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('sentence_synonym_customadmin')
        
        elif 'update' in request.POST:
            synonym_id = request.POST.get('synonym_id')
            synonym = get_object_or_404(SentenceSynonym, pk=synonym_id)
            form = SentenceSynonymForm(request.POST, instance=synonym)
            if form.is_valid():
                form.save()
                return redirect('sentence_synonym_customadmin')
        
        elif 'delete' in request.POST:
            synonym_id = request.POST.get('synonym_id')
            synonym = get_object_or_404(SentenceSynonym, pk=synonym_id)
            synonym.delete()
            return redirect('sentence_synonym_customadmin')

    form = SentenceSynonymForm()
    return render(request, 'sentence_synonym_customadmin.html', {
        'synonyms': synonyms,
        'form': form,
    })


from .forms import SentencePunctuationForm

def sentence_punctuation_customadmin(request):
    sentences = SentencePunctuation.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = SentencePunctuationForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('sentence_punctuation_customadmin')
        
        elif 'update' in request.POST:
            sentence_id = request.POST.get('sentence_id')
            sentence = get_object_or_404(SentencePunctuation, pk=sentence_id)
            form = SentencePunctuationForm(request.POST, instance=sentence)
            if form.is_valid():
                form.save()
                return redirect('sentence_punctuation_customadmin')
        
        elif 'delete' in request.POST:
            sentence_id = request.POST.get('sentence_id')
            sentence = get_object_or_404(SentencePunctuation, pk=sentence_id)
            sentence.delete()
            return redirect('sentence_punctuation_customadmin')

    form = SentencePunctuationForm()
    return render(request, 'sentence_punctuation_customadmin.html', {
        'sentences': sentences,
        'form': form,
    })


from .forms import StoryForm, StoryPartForm, StoryQuestionForm

def story_customadmin(request):
    stories = Story.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = StoryForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('story_customadmin')
        
        elif 'update' in request.POST:
            story_id = request.POST.get('story_id')
            story = get_object_or_404(Story, pk=story_id)
            form = StoryForm(request.POST, request.FILES, instance=story)
            if form.is_valid():
                form.save()
                return redirect('story_customadmin')
        
        elif 'delete' in request.POST:
            story_id = request.POST.get('story_id')
            story = get_object_or_404(Story, pk=story_id)
            story.delete()
            return redirect('story_customadmin')

    form = StoryForm()
    return render(request, 'story_customadmin.html', {
        'stories': stories,
        'form': form,
    })

def story_part_customadmin(request):
    story_parts = StoryPart.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = StoryPartForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('story_part_customadmin')
        
        elif 'update' in request.POST:
            part_id = request.POST.get('part_id')
            part = get_object_or_404(StoryPart, pk=part_id)
            form = StoryPartForm(request.POST, request.FILES, instance=part)
            if form.is_valid():
                form.save()
                return redirect('story_part_customadmin')
        
        elif 'delete' in request.POST:
            part_id = request.POST.get('part_id')
            part = get_object_or_404(StoryPart, pk=part_id)
            part.delete()
            return redirect('story_part_customadmin')

    form = StoryPartForm()
    return render(request, 'story_part_customadmin.html', {
        'story_parts': story_parts,
        'form': form,
    })

def story_question_customadmin(request):
    questions = StoryQuestion.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = StoryQuestionForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('story_question_customadmin')
        
        elif 'update' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(StoryQuestion, pk=question_id)
            form = StoryQuestionForm(request.POST, instance=question)
            if form.is_valid():
                form.save()
                return redirect('story_question_customadmin')
        
        elif 'delete' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(StoryQuestion, pk=question_id)
            question.delete()
            return redirect('story_question_customadmin')

    form = StoryQuestionForm()
    return render(request, 'story_question_customadmin.html', {
        'questions': questions,
        'form': form,
    })

### ---------------- Lecture Slides ---------------- ###

from django.core.exceptions import PermissionDenied
from django.http import Http404

@login_required
def slide_view(request, slide_id=None):
    try:
        # Get user profile and accessible levels
        user_profile = request.user.userprofile
        levels = Level.objects.filter(order__lte=user_profile.related_level.order)
        slide = None
        contents = None
        selected_level_id = None
        selected_module_id = None
        next_slide = None

        # Unlock the first slide logic
        first_unlocked = False
        for level in levels.order_by('order'):
            user_level_progress, created = UserLevelProgress.objects.get_or_create(user=request.user, level=level)
            if user_level_progress.is_locked and not first_unlocked:
                user_level_progress.is_locked = False
                user_level_progress.save()
                first_unlocked = True

            first_module = level.modules.order_by('order').first()
            if first_module:
                user_module_progress, created = UserModuleProgress.objects.get_or_create(user=request.user, module=first_module)
                if user_module_progress.is_locked and not first_unlocked:
                    user_module_progress.is_locked = False
                    user_module_progress.save()

                first_slide = first_module.slides.order_by('order').first()
                if first_slide:
                    user_slide_progress, created = UserSlideProgress.objects.get_or_create(user=request.user, slide=first_slide)
                    if not user_slide_progress.is_completed and not first_unlocked:
                        user_slide_progress.is_completed = True
                        user_slide_progress.save()
                        first_unlocked = True
                    break

        if slide_id:
            # Get the current slide
            slide = get_object_or_404(Slide, id=slide_id)

            # Check if the slide belongs to a locked level
            user_level_progress = UserLevelProgress.objects.filter(user=request.user, level=slide.module.level).first()
            if not user_level_progress or user_level_progress.is_locked:
                messages.error(request, "You cannot access slides in a locked level. Please complete the previous levels first.")
                return redirect('e_learning:level_overview')  # Redirect to an overview page

            # Track user progress for the slide
            user_slide_progress, created = UserSlideProgress.objects.get_or_create(user=request.user, slide=slide)
            if 'mark_completed' in request.GET:
                user_slide_progress.is_completed = True
                user_slide_progress.completed_at = timezone.now()
                user_slide_progress.save()

            # Get slide contents and navigation details
            contents = slide.contents.order_by('order')
            selected_level_id = slide.module.level.id
            selected_module_id = slide.module.id

            # Determine the next slide
            next_slide = (
                Slide.objects.filter(module=slide.module, order__gt=slide.order)
                .order_by('order')
                .first()
            )

            # If no next slide, find the first slide in the next module
            if not next_slide:
                next_module = (
                    Module.objects.filter(level=slide.module.level, order__gt=slide.module.order)
                    .order_by('order')
                    .first()
                )
                if next_module:
                    next_slide = next_module.slides.order_by('order').first()

        # Prepare a progress dictionary for rendering
        user_slide_progress_dict = {
            slide.id: {
                'is_completed': (
                    slide.user_progress.filter(user=request.user).first().is_completed
                    if slide.user_progress.filter(user=request.user).exists() else False
                )
            }
            for slide in Slide.objects.all()
        }

        return render(request, 'e_learning/slide_view.html', {
            'levels': levels,
            'selected_slide': slide,
            'slide_contents': contents,
            'selected_level_id': selected_level_id,
            'selected_module_id': selected_module_id,
            'next_slide': next_slide,
            'user_slide_progress_dict': user_slide_progress_dict,
        })

    except PermissionDenied:
        # Handle permission errors explicitly
        messages.error(request, "You do not have permission to access this resource.")
        return redirect('home')  # Redirect to a safe fallback page

    except Http404:
        # Handle not-found errors explicitly
        messages.error(request, "The requested slide was not found.")
        return redirect('level_overview')  # Redirect to a fallback page

    except Exception as e:
        # Catch-all for unexpected errors
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect('home')  # Redirect to a safe fallback page

def submit_slide_question(request, slide_id):
    slide = get_object_or_404(Slide, id=slide_id)
    question = slide.question

    choices = {
        1: question.choice1,
        2: question.choice2,
        3: question.choice3,
        4: question.choice4,
    }

    if request.method == "POST":
        selected_answer = int(request.POST.get("answer", 0))
        if selected_answer == question.correct_answer:
            correct_answer_text = choices.get(question.correct_answer, "Unknown")
            messages.success(request, f"መልሱን በትክክል አግኝተዋል፡፡ ጎበዝ ጎበዝ 👍🏻 Answer: {correct_answer_text}")
        else:
            messages.error(request, "እንደገና ይሞክሩ!!!")

    return redirect('view_slide', slide_id=slide.id)

## ----------------------------------

def manage_levels(request):
    levels = Level.objects.all()
    if request.method == 'POST':
        form = LevelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_levels')
    else:
        form = LevelForm()
    return render(request, 'admin/manage_levels.html', {'levels': levels, 'form': form})


def manage_modules(request, level_id):
    level = get_object_or_404(Level, id=level_id)
    modules = Module.objects.filter(level=level).order_by('order')
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.level = level
            module.save()
            return redirect('manage_modules', level_id=level.id)
    else:
        form = ModuleForm()
    return render(request, 'admin/manage_modules.html', {'level': level, 'modules': modules, 'form': form})


def manage_slides(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    slides = Slide.objects.filter(module=module).order_by('order')
    if request.method == 'POST':
        form = SlideForm(request.POST)
        if form.is_valid():
            slide = form.save(commit=False)
            slide.module = module
            slide.save()
            return redirect('manage_slides', module_id=module.id)
    else:
        form = SlideForm()
    return render(request, 'admin/manage_slides.html', {'module': module, 'slides': slides, 'form': form})

def create_slide_content(request, slide_id):
    slide = get_object_or_404(Slide, id=slide_id)
    contents = SlideContent.objects.filter(slide=slide).order_by('order')  # Fetch slide contents

    # Handle SlideQuestion form submission
    if request.method == 'POST':
        # Handle SlideContent form
        content_form = SlideContentForm(request.POST, request.FILES)
        if content_form.is_valid():
            content = content_form.save(commit=False)
            content.slide = slide
            content.save()

        # Handle SlideQuestion form
        question_form = SlideQuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.slide = slide  # Associate the question with the current slide
            question.save()

        return redirect('create_slide_content', slide_id=slide.id)
    
    else:
        content_form = SlideContentForm()
        question_form = SlideQuestionForm()

    return render(
        request, 
        'admin/create_slide_content.html', 
        {
            'slide': slide, 
            'content_form': content_form, 
            'question_form': question_form,
            'contents': contents
        }
    )


#custom admin continued 
from .forms import LevelForm

def level_customadmin(request):
    levels = Level.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST:
            form = LevelForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('level_customadmin')
        
        elif 'update' in request.POST:
            level_id = request.POST.get('level_id')
            level = get_object_or_404(Level, pk=level_id)
            form = LevelForm(request.POST, instance=level)
            if form.is_valid():
                form.save()
                return redirect('level_customadmin')
        
        elif 'delete' in request.POST:
            level_id = request.POST.get('level_id')
            level = get_object_or_404(Level, pk=level_id)
            level.delete()
            return redirect('level_customadmin')

    form = LevelForm()
    return render(request, 'level_customadmin.html', {
        'levels': levels,
        'form': form,
    })


from .forms import ModuleForm

def module_customadmin(request):
    modules = Module.objects.all()
    levels = Level.objects.all()  # Get all levels for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = ModuleForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('module_customadmin')
        
        elif 'update' in request.POST:
            module_id = request.POST.get('module_id')
            module = get_object_or_404(Module, pk=module_id)
            form = ModuleForm(request.POST, instance=module)
            if form.is_valid():
                form.save()
                return redirect('module_customadmin')
        
        elif 'delete' in request.POST:
            module_id = request.POST.get('module_id')
            module = get_object_or_404(Module, pk=module_id)
            module.delete()
            return redirect('module_customadmin')

    form = ModuleForm()
    return render(request, 'module_customadmin.html', {
        'modules': modules,
        'levels': levels,
        'form': form,
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import Slide, Module
from .forms import SlideForm

def slide_customadmin(request):
    slides = Slide.objects.all()
    modules = Module.objects.all()  # Get all modules for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = SlideForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('slide_customadmin')
        
        elif 'update' in request.POST:
            slide_id = request.POST.get('slide_id')
            slide = get_object_or_404(Slide, pk=slide_id)
            form = SlideForm(request.POST, instance=slide)
            if form.is_valid():
                form.save()
                return redirect('slide_customadmin')
        
        elif 'delete' in request.POST:
            slide_id = request.POST.get('slide_id')
            slide = get_object_or_404(Slide, pk=slide_id)
            slide.delete()
            return redirect('slide_customadmin')

    form = SlideForm()
    return render(request, 'slide_customadmin.html', {
        'slides': slides,
        'modules': modules,
        'form': form,
    })



from .forms import SlideContentForm

def slide_content_customadmin(request):
    slide_contents = SlideContent.objects.all()
    slides = Slide.objects.all()  # Get all slides for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = SlideContentForm(request.POST, request.FILES)  # Include request.FILES for file uploads
            if form.is_valid():
                form.save()
                return redirect('slide_content_customadmin')
        
        elif 'update' in request.POST:
            content_id = request.POST.get('content_id')
            content = get_object_or_404(SlideContent, pk=content_id)
            form = SlideContentForm(request.POST, request.FILES, instance=content)
            if form.is_valid():
                form.save()
                return redirect('slide_content_customadmin')
        
        elif 'delete' in request.POST:
            content_id = request.POST.get('content_id')
            content = get_object_or_404(SlideContent, pk=content_id)
            content.delete()
            return redirect('slide_content_customadmin')

    form = SlideContentForm()
    return render(request, 'slide_content_customadmin.html', {
        'slide_contents': slide_contents,
        'slides': slides,
        'form': form,
    })

from .forms import SlideQuestionForm

def slide_question_customadmin(request):
    slide_questions = SlideQuestion.objects.all()
    slides = Slide.objects.all()  # Get all slides for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = SlideQuestionForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('slide_question_customadmin')
        
        elif 'update' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(SlideQuestion, pk=question_id)
            form = SlideQuestionForm(request.POST, instance=question)
            if form.is_valid():
                form.save()
                return redirect('slide_question_customadmin')
        
        elif 'delete' in request.POST:
            question_id = request.POST.get('question_id')
            question = get_object_or_404(SlideQuestion, pk=question_id)
            question.delete()
            return redirect('slide_question_customadmin')

    form = SlideQuestionForm()
    return render(request, 'slide_question_customadmin.html', {
        'slide_questions': slide_questions,
        'slides': slides,
        'form': form,
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import UserSlideProgress, Slide
from .forms import UserSlideProgressForm
from django.contrib.auth.models import User

def user_slide_progress_customadmin(request):
    progress_records = UserSlideProgress.objects.all()
    slides = Slide.objects.all()  # Get all slides for the dropdown
    users = User.objects.all()  # Get all users for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = UserSlideProgressForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('user_slide_progress_customadmin')
        
        elif 'update' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserSlideProgress, pk=progress_id)
            form = UserSlideProgressForm(request.POST, instance=progress)
            if form.is_valid():
                form.save()
                return redirect('user_slide_progress_customadmin')
        
        elif 'delete' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserSlideProgress, pk=progress_id)
            progress.delete()
            return redirect('user_slide_progress_customadmin')

    form = UserSlideProgressForm()
    return render(request, 'user_slide_progress_customadmin.html', {
        'progress_records': progress_records,
        'slides': slides,
        'users': users,
        'form': form,
    })


from .forms import UserLevelProgressForm

def user_level_progress_customadmin(request):
    progress_records = UserLevelProgress.objects.all()
    levels = Level.objects.all()  # Get all levels for the dropdown
    users = User.objects.all()    # Get all users for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = UserLevelProgressForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('user_level_progress_customadmin')
        
        elif 'update' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserLevelProgress, pk=progress_id)
            form = UserLevelProgressForm(request.POST, instance=progress)
            if form.is_valid():
                form.save()
                return redirect('user_level_progress_customadmin')
        
        elif 'delete' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserLevelProgress, pk=progress_id)
            progress.delete()
            return redirect('user_level_progress_customadmin')

    form = UserLevelProgressForm()
    return render(request, 'user_level_progress_customadmin.html', {
        'progress_records': progress_records,
        'levels': levels,
        'users': users,
        'form': form,
    })


from .forms import UserModuleProgressForm

def user_module_progress_customadmin(request):
    progress_records = UserModuleProgress.objects.all()
    modules = Module.objects.all()  # Get all modules for the dropdown
    users = User.objects.all()       # Get all users for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = UserModuleProgressForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('user_module_progress_customadmin')
        
        elif 'update' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserModuleProgress, pk=progress_id)
            form = UserModuleProgressForm(request.POST, instance=progress)
            if form.is_valid():
                form.save()
                return redirect('user_module_progress_customadmin')
        
        elif 'delete' in request.POST:
            progress_id = request.POST.get('progress_id')
            progress = get_object_or_404(UserModuleProgress, pk=progress_id)
            progress.delete()
            return redirect('user_module_progress_customadmin')

    form = UserModuleProgressForm()
    return render(request, 'user_module_progress_customadmin.html', {
        'progress_records': progress_records,
        'modules': modules,
        'users': users,
        'form': form,
    })


from .forms import UserProfileForm

def user_profile_customadmin(request):
    profiles = UserProfile.objects.all()
    levels = Level.objects.all()  # Get all levels for the dropdown
    users = User.objects.all()     # Get all users for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = UserProfileForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('user_profile_customadmin')
        
        elif 'update' in request.POST:
            profile_id = request.POST.get('profile_id')
            profile = get_object_or_404(UserProfile, pk=profile_id)
            form = UserProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                return redirect('user_profile_customadmin')
        
        elif 'delete' in request.POST:
            profile_id = request.POST.get('profile_id')
            profile = get_object_or_404(UserProfile, pk=profile_id)
            profile.delete()
            return redirect('user_profile_customadmin')

    form = UserProfileForm()
    return render(request, 'user_profile_customadmin.html', {
        'profiles': profiles,
        'levels': levels,
        'users': users,
        'form': form,
    })


from .forms import PointHistoryForm

def point_history_customadmin(request):
    histories = PointHistory.objects.all()
    profiles = UserProfile.objects.all()  # Get all user profiles for the dropdown

    if request.method == 'POST':
        if 'create' in request.POST:
            form = PointHistoryForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('point_history_customadmin')
        
        elif 'update' in request.POST:
            history_id = request.POST.get('history_id')
            history = get_object_or_404(PointHistory, pk=history_id)
            form = PointHistoryForm(request.POST, instance=history)
            if form.is_valid():
                form.save()
                return redirect('point_history_customadmin')
        
        elif 'delete' in request.POST:
            history_id = request.POST.get('history_id')
            history = get_object_or_404(PointHistory, pk=history_id)
            history.delete()
            return redirect('point_history_customadmin')

    form = PointHistoryForm()
    return render(request, 'point_history_customadmin.html', {
        'histories': histories,
        'profiles': profiles,
        'form': form,
    })