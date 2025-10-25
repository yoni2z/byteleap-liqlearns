from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, WordCharade, WritingSubmission, Video, VoiceRecording, Event, LetterSound, WordAudio, WordVideo, WordCountdownRecording, Sentence, Passage

class UserRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    referral_code = forms.CharField(max_length=10, required=False, label="Referral Code")

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'password1', 'password2', 'referral_code']

class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['full_name', 'rank', 'level', 'aura', 'aura_points']

### -------------- Lecture Slide ------------ ###

from django import forms
from .models import Level, Module, Slide, SlideContent, SlideQuestion

class LevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = ['name', 'description', 'order', 'price']


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['name', 'description', 'order']


class SlideForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = ['title', 'order']


class SlideContentForm(forms.ModelForm):
    class Meta:
        model = SlideContent
        fields = ['content_type', 'text_content', 'image_content', 'video_content', 'order']

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        text_content = cleaned_data.get('text_content')
        image_content = cleaned_data.get('image_content')
        video_content = cleaned_data.get('video_content')

        if content_type == 'Text' and not text_content:
            raise forms.ValidationError("Text content is required for content type 'Text'.")
        if content_type == 'Image' and not image_content:
            raise forms.ValidationError("Image content is required for content type 'Image'.")
        if content_type == 'Video' and not video_content:
            raise forms.ValidationError("Video content is required for content type 'Video'.")
        return cleaned_data
    
class SlideQuestionForm(forms.ModelForm):
    class Meta:
        model = SlideQuestion
        fields = ['question_text', 'choice1', 'choice2', 'choice3', 'choice4', 'correct_answer']

### ------------------ ##########

class WordCharadeForm(forms.ModelForm):
    class Meta:
        model = WordCharade
        fields = ['recording']

    
#tony
class WritingSubmissionForm(forms.ModelForm):
    class Meta:
        model = WritingSubmission
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write about anything you want here...'}),
        }

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'video_file']  # Include the video_file field here


class ParagraphAudioForm(forms.Form):
    audio_file = forms.FileField()


class VoiceRecordingForm(forms.ModelForm):
    class Meta:
        model = VoiceRecording
        fields = ['student_name', 'audio_file']

    

#custom admin related
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_date', 'end_date', 'location', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event Title',
                'style': 'border-radius: 8px;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Event Description',
                'rows': 4,
                'style': 'border-radius: 8px;'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'style': 'border-radius: 8px;'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'style': 'border-radius: 8px;'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event Location',
                'style': 'border-radius: 8px;'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'style': 'border-radius: 8px;'
            }),
        }

class LetterSoundForm(forms.ModelForm):
    class Meta:
        model = LetterSound
        fields = ['letter', 'sound_field']
        
    letter = forms.CharField(max_length=1, widget=forms.TextInput(attrs={'class': 'form-control'}))
    sound_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

from django import forms
from .models import WordAudio

class WordAudioForm(forms.ModelForm):
    class Meta:
        model = WordAudio
        fields = ['word', 'audio_file', 'image', 'definition', 'acceptable_characters']
        widgets = {
            'word': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the word',
                'style': 'border-radius: 8px;'
            }),
            'audio_file': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'style': 'border-radius: 8px;'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'style': 'border-radius: 8px;'
            }),
            'definition': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the definition',
                'rows': 4,
                'style': 'border-radius: 8px;'
            }),
            'acceptable_characters': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter acceptable characters',
                'style': 'border-radius: 8px;'
            }),
        }

class WordVideoForm(forms.ModelForm):
    class Meta:
        model = WordVideo
        fields = ['word', 'video_file', 'hint']

class WordCountdownRecordingForm(forms.ModelForm):
    class Meta:
        model = WordCountdownRecording
        fields = ['user', 'letter', 'audio_file']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'letter': forms.Select(attrs={'class': 'form-control'}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class SentenceForm(forms.ModelForm):
    class Meta:
        model = Sentence
        fields = ['sentence', 'definition', 'is_active']

class PassageForm(forms.ModelForm):
    class Meta:
        model = Passage
        fields = ['paragraph', 'main_idea', 'wrong_choices']


from .models import DescriptiveImage, DescriptiveSentenceQuestion

class DescriptiveImageForm(forms.ModelForm):
    class Meta:
        model = DescriptiveImage
        fields = ['image', 'correct_word']

class DescriptiveSentenceQuestionForm(forms.ModelForm):
    class Meta:
        model = DescriptiveSentenceQuestion
        fields = ['image', 'correct_sentence']


from .models import FillInTheBlank, Numbers

class FillInTheBlankForm(forms.ModelForm):
    class Meta:
        model = FillInTheBlank
        fields = ['question', 'correct_answer']

class NumbersForm(forms.ModelForm):
    class Meta:
        model = Numbers
        fields = ['number', 'word', 'amharic_word']


from .models import WritingSubmission, Video, VideoResponse, WordAudioRecording, Paragraph, VoiceRecording

class WritingSubmissionForm(forms.ModelForm):
    class Meta:
        model = WritingSubmission
        fields = ['user', 'content']  # User should be selected from the admin

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'video_file']


class VideoResponseForm(forms.ModelForm):
    class Meta:
        model = VideoResponse
        fields = ['video', 'student', 'response']

class WordAudioRecordingForm(forms.ModelForm):
    class Meta:
        model = WordAudioRecording
        fields = ['word_audio', 'user', 'recording_file']


class ParagraphForm(forms.ModelForm):
    class Meta:
        model = Paragraph
        fields = ['content', 'definition', 'is_active']

class VoiceRecordingForm(forms.ModelForm):
    class Meta:
        model = VoiceRecording
        fields = ['student_name', 'audio_file']

from .models import ParagraphCreation, AmharicLetterFamily, AmharicLetterAudio

class ParagraphCreationForm(forms.ModelForm):
    class Meta:
        model = ParagraphCreation
        fields = ['correct_paragraph', 'sentences']

class AmharicLetterFamilyForm(forms.ModelForm):
    class Meta:
        model = AmharicLetterFamily
        fields = ['letter', 'family']

class AmharicLetterAudioForm(forms.ModelForm):
    class Meta:
        model = AmharicLetterAudio
        fields = ['family', 'letter', 'audio_file']



from .models import LetterFillIn, NumberToWord

class LetterFillInForm(forms.ModelForm):
    class Meta:
        model = LetterFillIn
        fields = ['correct_word', 'display_word', 'correct_letter', 'choices', 'meaning']

class NumberToWordForm(forms.ModelForm):
    class Meta:
        model = NumberToWord
        fields = ['number', 'amharic_number', 'number_name']

from .models import AmharicEnglishMatching, SentenceSynonym, SentencePunctuation

class AmharicEnglishMatchingForm(forms.ModelForm):
    class Meta:
        model = AmharicEnglishMatching
        fields = ['amharic_sentence', 'english_sentence']

class SentenceSynonymForm(forms.ModelForm):
    class Meta:
        model = SentenceSynonym
        fields = ['sentence', 'correct_word', 'hint']

class SentencePunctuationForm(forms.ModelForm):
    class Meta:
        model = SentencePunctuation
        fields = ['text', 'correct_text', 'choices', 'correct_answer']


from .models import Story, StoryPart, StoryQuestion

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['title', 'description', 'cover_image']

class StoryPartForm(forms.ModelForm):
    class Meta:
        model = StoryPart
        fields = ['story', 'part_number', 'audio_file', 'video_file', 'text_content']

class StoryQuestionForm(forms.ModelForm):
    class Meta:
        model = StoryQuestion
        fields = ['part', 'question_text', 'correct_answer', 'options']

from .models import Level

class LevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = ['name', 'description', 'order', 'price']          

from .models import Module

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['name', 'description', 'level', 'order']

from .models import Slide

class SlideForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = ['title', 'module', 'order']

class SlideContentForm(forms.ModelForm):
    class Meta:
        model = SlideContent
        fields = ['slide', 'content_type', 'text_content', 'image_content', 'video_content', 'order']

class SlideQuestionForm(forms.ModelForm):
    class Meta:
        model = SlideQuestion
        fields = ['slide', 'question_text', 'choice1', 'choice2', 'choice3', 'choice4', 'correct_answer']

from .models import UserSlideProgress
class UserSlideProgressForm(forms.ModelForm):
    class Meta:
        model = UserSlideProgress
        fields = ['user', 'slide', 'is_completed', 'completed_at']


from .models import UserLevelProgress

class UserLevelProgressForm(forms.ModelForm):
    class Meta:
        model = UserLevelProgress
        fields = ['user', 'level', 'is_locked']

from .models import UserModuleProgress

class UserModuleProgressForm(forms.ModelForm):
    class Meta:
        model = UserModuleProgress
        fields = ['user', 'module', 'is_locked']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['user', 'full_name', 'referral_code', 'rank', 'level', 'related_level', 
                  'aura', 'aura_points', 'is_subscribed', 'last_login_bonus_date', 'referred_by']
        
from .models import PointHistory      
class PointHistoryForm(forms.ModelForm):
    class Meta:
        model = PointHistory
        fields = ['user_profile', 'points', 'reason']