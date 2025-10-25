import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now

### -------------- Lecture Slide -------------- ### 

class Level(models.Model):
    name = models.CharField(max_length=100)  # e.g., Beginner, Basic, Advanced, Pro
    description = models.TextField()
    order = models.PositiveIntegerField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=10)  # Price in USD

    def __str__(self):
        return self.name

class Module(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.name} - {self.level}"

class Slide(models.Model):
    title = models.CharField(max_length=200)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='slides')
    order = models.PositiveIntegerField()  # Sequence order in module

    def __str__(self):
        return f"{self.title} - {self.module}"


class SlideContent(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('Text', 'Text'),
        ('Image', 'Image'),
        ('Video', 'Video'),
    )

    slide = models.ForeignKey(Slide, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    text_content = models.TextField(blank=True, null=True)  # Optional for text
    image_content = models.ImageField(upload_to='slide_images/', blank=True, null=True)  # Images in "slide_images/" folder
    video_content = models.FileField(upload_to='slide_videos/', blank=True, null=True)  # Videos in "slide_videos/" folder
    order = models.PositiveIntegerField()  # Sequence order within the slide

    def __str__(self):
        return f"Content {self.id} - {self.slide.title} ({self.content_type})"
    
class SlideQuestion(models.Model):
    slide = models.OneToOneField(Slide, on_delete=models.CASCADE, related_name='question')
    question_text = models.TextField()
    choice1 = models.CharField(max_length=255)
    choice2 = models.CharField(max_length=255)
    choice3 = models.CharField(max_length=255)
    choice4 = models.CharField(max_length=255)
    correct_answer = models.PositiveIntegerField()  # 1, 2, 3, or 4 for the correct choice

    def __str__(self):
        return f"Question for Slide: {self.slide.title}"

    
class UserSlideProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slide_progress')
    slide = models.ForeignKey(Slide, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)  # Tracks if the user completed the slide
    completed_at = models.DateTimeField(null=True, blank=True)  # Optional timestamp for completion

    def __str__(self):
        return f"{self.user} - {self.slide} - {'Completed' if self.is_completed else 'In Progress'}"
    
class UserLevelProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='level_progress')
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='user_progress')
    is_locked = models.BooleanField(default=True)  # User-specific lock status

    def __str__(self):
        return f"{self.user} - {self.level} - {'Locked' if self.is_locked else 'Unlocked'}"


class UserModuleProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='user_progress')
    is_locked = models.BooleanField(default=True)  # User-specific lock status

    def __str__(self):
        return f"{self.user} - {self.module} - {'Locked' if self.is_locked else 'Unlocked'}"

    
### --------------------------------------------

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    referral_code = models.CharField(max_length=10, unique=True)
    rank = models.CharField(max_length=100)
    level = models.CharField(max_length=100, default='1')
    related_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)  # ForeignKey to the Level model
    aura = models.CharField(max_length=100, default='None')
    aura_points = models.IntegerField(default=0)
    is_subscribed = models.BooleanField(default=False)
    last_login_bonus_date = models.DateField(null=True, blank=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')

    def __str__(self):
        return self.full_name

    @staticmethod
    def generate_referral_code():
        """Generate a unique referral code."""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        while UserProfile.objects.filter(referral_code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return code
    
    def successful_referrals_this_week(self):
        """Count successful referrals made during the current week."""
        start_of_week = now().date() - timedelta(days=now().weekday())  # Monday
        return PointHistory.objects.filter(
            user_profile=self,
            reason__startswith="Referral Bonus",
            created_at__gte=start_of_week
        ).count()

# point history model

class PointHistory(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='point_history')
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_profile} - {self.reason}"
    
# point history model

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)

    def __str__(self):
        return self.title
    

# for the sound memory game

class LetterSound(models.Model):
    letter = models.CharField(max_length=1)
    sound_field = models.FileField(upload_to='sounds/')

    def __str__(self):
        return self.letter
    
# sound memory game end

# for audio recognition

class WordAudio(models.Model):
    word = models.CharField(max_length=100)
    audio_file = models.FileField(upload_to='word_audios/')
    image = models.ImageField(upload_to='word_images/', null=True, blank=True)  # Optional image field
    definition = models.TextField(null=True, blank=True)  # Make the field optional
    acceptable_characters = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.word


# audio recognition

# for word video

class WordVideo(models.Model):
    word = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='word_video/')
    hint = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.word

# for word video

#tony
class LetterVideo(models.Model):
    letter_set = models.CharField(max_length=255)  # Example: "A, B, C, D"
    video = models.FileField(upload_to='videos/')  # Store uploaded videos in the 'videos/' directory

    def __str__(self):
        return f"Letters: {self.letter_set}"

#tony 
class LetterImage(models.Model):
    letter = models.CharField(max_length=1)
    image = models.ImageField(upload_to='letter_images/')  # Make sure to set up media files

    def __str__(self):
        return self.letter
    
# word charades in speaking

class WordCharade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Generic relation to support multiple models as 'question'
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    question = GenericForeignKey('content_type', 'object_id')

    recording = models.FileField(upload_to='recordings/')
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question} - {self.sent_at}"

    @staticmethod
    def delete_old_recordings():
        """Delete recordings older than 3 days."""
        threshold = timezone.now() - timedelta(days=3)
        WordCharade.objects.filter(sent_at__lt=threshold).delete()

# word countdown start

class WordCountdownRecording(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    letter = models.ForeignKey(LetterImage, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='word_countdown_recordings/')
    submission_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.letter.letter}"
    
# word countdown end

# sentence matching start 

class Sentence(models.Model):
    sentence = models.CharField(max_length=255)
    definition = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.sentence

# sentence matching end

# Passage Model

class Passage(models.Model):
    paragraph = models.TextField()
    main_idea = models.CharField(max_length=255)
    wrong_choices = models.JSONField()

    def __str__(self):
        return self.paragraph[:50] 
# Passage Model


#tony
class BingoItem(models.Model):
    ITEM_TYPE_CHOICES = (
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('video', 'Video'),
    )

    title = models.CharField(max_length=100)
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    image = models.ImageField(upload_to='bingo/images/', blank=True, null=True)
    audio = models.FileField(upload_to='bingo/audio/', blank=True, null=True)
    video_file = models.FileField(upload_to='bingo/videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class BingoQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    correct_item = models.ForeignKey(BingoItem, on_delete=models.CASCADE, related_name='correct_answers')
    options = models.ManyToManyField(BingoItem, related_name='option_in_questions')

    def __str__(self):
        return f"Question: {self.question_text}"


class LetterSoundSequence(models.Model):
    sounds = models.ManyToManyField(LetterSound)
    correct_order = models.TextField()  # Store the correct order as a comma-separated string

    def __str__(self):
        return ', '.join(str(sound) for sound in self.sounds.all())

#tony
#for the picture to word game
class DescriptiveImage(models.Model):
    image = models.ImageField(upload_to='descriptive_images/')
    correct_word = models.CharField(max_length=50)  # Correct descriptive word

    def __str__(self):
        return f"Image with description '{self.correct_word}'"
    
class DescriptiveSentenceQuestion(models.Model):
    image = models.ImageField(upload_to='descriptive_images/')
    correct_sentence = models.TextField(help_text="The correct sentence that describes the image")

    def __str__(self):
        return f"Question {self.id}"
    
##tonyy
class FillInTheBlank(models.Model):
    question = models.TextField(help_text="Write the sentence with blanks represented by '__'.")
    correct_answer = models.CharField(max_length=255, help_text="Write the correct answer(s) for the blank(s), separated by commas if multiple.")

    def __str__(self):
        return self.question
    
class Numbers(models.Model):
    number = models.IntegerField(help_text="The number (e.g. 1, 2, 3).")
    word = models.CharField(max_length=100, help_text="The word representation of the number in English (e.g. one, two, three).")
    amharic_word = models.CharField(max_length=100, help_text="The word representation of the number in Amharic (e.g. ፩, ፪, ፫).", null=True, blank=True)

    def __str__(self):
        return f"{self.number} - {self.word} / {self.amharic_word}"

class WritingSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # To link to the logged-in user
    content = models.TextField(help_text="Write anything you'd like here.")
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission by {self.user.username} on {self.date_submitted}"
    

#video to paragraph game
class Video(models.Model):
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    
    def __str__(self):
        return self.title

class VideoResponse(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='responses')
    student = models.ForeignKey('auth.User', on_delete=models.CASCADE)  # or a custom user model
    response = models.TextField(help_text="The student's description of the video")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response by {self.student.username} for {self.video.title}"

class WordAudioRecording(models.Model):
    word_audio = models.ForeignKey(WordAudio, on_delete=models.CASCADE, related_name='recordings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Assuming you have a User model
    recording_file = models.FileField(upload_to='user_recordings/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.word_audio.word}"
    
class Paragraph(models.Model):
    content = models.TextField()  # Paragraph content
    definition = models.TextField(blank=True, null=True)  # Optional definition/description
    is_active = models.BooleanField(default=True)  # Status of the paragraph

    def __str__(self):
        return f"Paragraph {self.id}"
    
class VoiceRecording(models.Model):
    student_name = models.CharField(max_length=100)
    audio_file = models.FileField(upload_to='uploads/voice_recordings/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.student_name
    


#from yonas

# Paragraph Creation

class ParagraphCreation(models.Model):
    correct_paragraph = models.TextField()
    correct_order = models.JSONField()
    sentences = models.JSONField()

    def save(self, *args, **kwargs):
        if isinstance(self.sentences, str):
            self.sentences = [sentence.strip() for sentence in self.sentences.split(',')]
        
        self.correct_order = self.sentences.copy()

        super(ParagraphCreation, self).save(*args, **kwargs) 

    def __str__(self):
        return self.correct_paragraph[:50]


# Paragraph Creation end

# Amharic Letter Family

class AmharicLetterFamily(models.Model):
    letter = models.CharField(max_length=1) 
    family = models.JSONField() 

    def __str__(self):
        return f"Family of {self.letter}"

# Amharic Letter family end

# Amharic Letter Audio

class AmharicLetterAudio(models.Model):
    family = models.ForeignKey(AmharicLetterFamily, on_delete=models.CASCADE, related_name="letters")
    letter = models.CharField(max_length=1)
    audio_file = models.FileField(upload_to='amharic_audio/')

    def __str__(self):
        return f"{self.letter} in {self.family.letter}'s family"

# Amharic Letter Audio end

# Letter Fill In

class LetterFillIn(models.Model):
    correct_word = models.CharField(max_length=100)
    display_word = models.CharField(max_length=100)
    correct_letter = models.CharField(max_length=1)
    choices = models.JSONField() 
    meaning = models.CharField(max_length=255)

    def __str__(self):
        return self.correct_word

# Letter Fill in end

# number to word

class NumberToWord(models.Model):
    number = models.PositiveIntegerField()
    amharic_number = models.CharField(max_length=20, help_text="put the equivalent amharic number e.g, ፩, ፯ ...")
    number_name = models.CharField(max_length=100, help_text="insert the number in words")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.number} -> {self.amharic_number} ({self.number_name})"

# number to word end

# amharic english matching

class AmharicEnglishMatching(models.Model):
    amharic_sentence = models.CharField(max_length=255)
    english_sentence = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.amharic_sentence} -> {self.english_sentence}"

# amharic english matching end

# sentence synonym

class SentenceSynonym(models.Model):
    sentence = models.TextField()
    correct_word = models.CharField(max_length=100)
    hint = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.sentence} - {self.correct_word}"

# sentence synonym end

# sentence punctuation

class SentencePunctuation(models.Model):
    text = models.TextField(help_text="The sentence to display without punctuation")
    correct_text = models.TextField(help_text="The correctly punctuated sentence")
    choices = models.CharField(
        max_length=100,
        help_text="Comma-separated punctuation choices (e.g., .,!,?,;,:)",
    )
    correct_answer = models.CharField(
        max_length=1,  # A single punctuation mark
        help_text="The correct punctuation mark for this sentence"
    )

    def __str__(self):
        return self.text

# sentence punctuation end

# story ----- for listening part

class Story(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='story_covers/', null=True, blank=True)

    def __str__(self):
        return f"{self.title}"

class StoryPart(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="parts")
    part_number = models.PositiveIntegerField()
    audio_file = models.FileField(upload_to='story_audios/')
    video_file = models.FileField(upload_to='story_videos/', null=True, blank=True)
    text_content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.story} - {self.part_number}"

class StoryQuestion(models.Model):
    part = models.ForeignKey(StoryPart, on_delete=models.CASCADE, related_name="questions")
    question_text = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=255)
    options = models.JSONField()  # Store options as a list of strings

    def __str__(self):
        return f"{self.part} - Question"

# story ---- for listening part
