# hahuapp/admin.py
from django.contrib import admin
from .models import (
    UserProfile,
    PointHistory,

    Event,
    LetterSound,
    WordAudio,
    WordVideo,
    LetterVideo,
    LetterImage,
    WordCharade,
    WordCountdownRecording,
    Sentence,
    Passage,
    BingoItem, BingoQuestion,
    DescriptiveImage,
    DescriptiveSentenceQuestion,
    FillInTheBlank,
    Numbers,
    WritingSubmission,
    Video,
    VideoResponse,
    WordAudioRecording,
    Paragraph,
    VoiceRecording,

    SentenceSynonym,
    SentencePunctuation,
    ParagraphCreation,
    AmharicLetterFamily,
    LetterFillIn,
    AmharicLetterAudio,
    NumberToWord,
    AmharicEnglishMatching,
    Story,
    StoryPart,
    StoryQuestion
) 

### ---------- Lecture Note ----------------- ###

from .models import Level, Module, Slide, SlideContent, SlideQuestion, UserSlideProgress, UserModuleProgress, UserLevelProgress

admin.site.register(UserSlideProgress)
admin.site.register(UserModuleProgress)
admin.site.register(UserLevelProgress)

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'order')

class SlideContentInline(admin.TabularInline):
    model = SlideContent
    extra = 1

class SlideQuestionInline(admin.StackedInline):
    model = SlideQuestion
    extra = 0  # Don't show empty forms by default

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')
    inlines = [SlideContentInline, SlideQuestionInline]

admin.site.register(UserProfile)
admin.site.register(PointHistory)
admin.site.register(Event)
admin.site.register(LetterSound)
admin.site.register(WordAudio)
admin.site.register(WordVideo)
admin.site.register(WordCharade)
admin.site.register(WordCountdownRecording)
admin.site.register(Sentence)
admin.site.register(Passage)

admin.site.register(SentenceSynonym)
admin.site.register(SentencePunctuation)
admin.site.register(ParagraphCreation)
admin.site.register(AmharicLetterFamily)
admin.site.register(LetterFillIn)
admin.site.register(AmharicLetterAudio)
admin.site.register(NumberToWord)
admin.site.register(AmharicEnglishMatching)
admin.site.register(Story)
admin.site.register(StoryPart)
admin.site.register(StoryQuestion)


#tony
admin.site.register(LetterVideo)
admin.site.register(LetterImage)
#tony
@admin.register(BingoItem)
class BingoItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type')

@admin.register(BingoQuestion)
class BingoQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'correct_item')
    filter_horizontal = ('options',)

#tony
admin.site.register(DescriptiveImage)
admin.site.register(DescriptiveSentenceQuestion)

@admin.register(FillInTheBlank)
class FillInTheBlankAdmin(admin.ModelAdmin):
    list_display = ('question', 'correct_answer')
    search_fields = ('question',)

    # Optional: Customize the admin interface to improve usability
    def get_queryset(self, request):
        # Filter out any unnecessary data if needed
        return super().get_queryset(request)

    # Optional: Provide helpful field hints
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "question":
            field.help_text = "Use '__' to indicate blanks in the sentence."
        return field
    
admin.site.register(Numbers)
admin.site.register(WritingSubmission)
admin.site.register(Video)
admin.site.register(VideoResponse)



@admin.register(WordAudioRecording)
class WordAudioRecordingAdmin(admin.ModelAdmin):
    list_display = ('word_audio', 'user', 'recording_file', 'uploaded_at')
    search_fields = ('word_audio__word', 'user__username')
    list_filter = ('uploaded_at',)

admin.site.register(Paragraph)

admin.site.register(VoiceRecording)


