from django.urls import path
from .views import (
    signup, 
    user_login, 
    user_logout, 
    user_profile, 
    payment_page, 
    success, 
    cancel, 
    award_points,

    letter_bingo_view, 
    letter_memory_view, 
    letter_sequencing_view,
    letter_fill_in_the_blanks_view,
    letter_sound_discrimination_view,
    letter_sound_memory_view,
    letter_sound_charades_view,
    letter_story_view,
    letter_fill_in_the_blanks_2_view,
    word_formation_view,
    scrambled_letters_view,
    timed_writing_view,
    listen_and_write_view,
    audio_recognition_view,
    letter_quiz_view,
    word_matching_view,
    word_hunt_view,
    word_sequencing_view,
    word_sound_identification_view,
    word_tracing_view,
    word_formation_2_view,
    word_dictaition_view,
    word_charades_view,
    letter_copy_view,
    match_and_write,
    reset_activity,
    letter_memory_game,
    sound_sorting,
    letter_sound_identification,
    sound_imitation,
    speaking_charades_view,
    word_countdown_view,
    feedback_view,
    word_sound_discrimination_view,
    word_sound_memory_view,
    listen_and_identify_view,
    word_sound_sequencing_view,
    sentence_matching_view,
    sentence_hunt_view, 
    passage_analysis_view,
    letter_hunt_view,
    photo_to_word_view,
    word_to_photo_view,
    video_to_word_view,
    sentence_synonym_view,
    sentence_punctuation_view,
    paragraph_creation_view,
    find_family_view,
    arrange_family_view,
    find_family_2_view,
    time_stamp_view,
    number_to_word_view,
    amharic_english_matching_view,
    games_page_view,
    story_telling_view,
    remembering_game,
    descriptive_image_game,
    descriptive_sentence_game,
    multiple_choice_view,
    leaderboard_view,
    home
)
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.latest_event, name='home'),  # Home page
    path('signup/', signup, name='signup'),  # Sign up page
    path('login/', user_login, name='login'),  # Login page
    path('logout/', user_logout, name='logout'),  # Logout page
    path('profile/', user_profile, name='user_profile'),  # Profile page
    path('award-points/', award_points, name='award-points'),

    path('events/', views.event_list, name='event_list'),  # Events page
    path('payment/', payment_page, name='payment_page'), # payment page
    path('payment/success/', success, name='success'), # payment success page
    path('payment/cancel/', cancel, name='cancel'), # payment cancelled page
    path('error/', views.error_page, name='error_page'), # error page
    path('games/letter-bingo/', letter_bingo_view, name='letter-bingo'), # letter bingo game
    path('games/letter-memory/', letter_memory_view, name='letter-memory'), #letter memory game
    path('games/letter-sequencing/', letter_sequencing_view, name='letter-sequencing'), # letter sequencing game
    path('games/letter-fill-in-the-blanks/', letter_fill_in_the_blanks_view, name='letter-fill-in-the-blanks'), # letter fill in the blanks game
    path('games/letter-sound-discrimination/', letter_sound_discrimination_view, name='letter-sound-discrimination'),
    path('games/letter-sound-memory/', letter_sound_memory_view, name="letter-sound-memory"),
    path('games/letter-sound-charades/', letter_sound_charades_view, name="letter-sound-charades"),
    path('games/letter-story/', letter_story_view, name="letter-story"),
    path('games/letter-fill-in-the-blanks-2/', letter_fill_in_the_blanks_2_view, name='letter-fill-in-the-blanks-2'),
    path('games/word-formation/', word_formation_view, name="word-formation"),
    path('games/scrambled-letters/', scrambled_letters_view, name="scrambled-letters"),
    path('games/timed-writing/', timed_writing_view, name="timed-writing"),
    path('games/listen-and-write/', listen_and_write_view, name="listen-and-write"),
    path('games/audio-recognition/', audio_recognition_view, name="audio-recognition"),
    path('games/letter-quiz/',  letter_quiz_view, name="letter-quiz"),
    path('games/word-matching/', word_matching_view, name="word-matching"),
    path('games/word-hunt/', word_hunt_view, name="word-hunt"),
    path('games/word-sequencing/', word_sequencing_view, name="word-sequencing"),
    path('games/word-sound-identification/', word_sound_identification_view, name="word-sound-identification"),
    path('games/word-tracing/', word_tracing_view, name="word-tracing"),
    path('games/word-formation-2/', word_formation_2_view, name="word-formation-2"),
    path('games/word-dictation/', word_dictaition_view, name="word-dictation"),
    path('games/word-charades/', word_charades_view, name="word-charades"),
    path('games/speaking-charades/', speaking_charades_view, name="speaking-charades"),
    path('games/word-countdown/', word_countdown_view, name="word-countdown"),
    path('feedback/', feedback_view, name='feedback'),
    path('games/word-sound-discrimination/', word_sound_discrimination_view, name="word-sound-discrimination"),
    path('games/word-sound-memory/', word_sound_memory_view, name="word-sound-memory"),
    path('games/listen-and-identify/', listen_and_identify_view, name="listen-and-identify"),
    path('games/word-sound-sequencing/', word_sound_sequencing_view, name="word-sound-sequencing"),
    path('games/sentence-matching/',  sentence_matching_view, name="sentence-matching"),
    path('games/sentence-hunt/', sentence_hunt_view, name="sentence-hunt"),
    path('games/passage-analysis/', passage_analysis_view, name="passage-analysis"),

    path('games/photo-to-word/', photo_to_word_view, name='photo-to-word'), # Reading
    path('games/word-to-photo/', word_to_photo_view, name='word-to-photo'), # Reading
    path('games/video-to-word/', video_to_word_view, name='video-to-word'), # Reading
    path('games/sentence-synonym/', sentence_synonym_view, name='sentence-synonym'),
    path('games/sentence-punctuation/', sentence_punctuation_view, name='sentence-punctuation'),
    path('games/paragraph-creation/', paragraph_creation_view, name='paragraph-creation'),
    path('games/find-family/', find_family_view, name='find-family'), # Reading
    path('games/arrange-family/', arrange_family_view, name='arrange-family'), # Reading
    path('games/find-family-2/', find_family_2_view, name='find-family-2'),
    path('games/time-stamp', time_stamp_view, name='time-stamp'),
    path('games/number-to-word/', number_to_word_view, name='number-to-word'),
    path('games/amharic-english-matching/', amharic_english_matching_view, name="amharic-english-matching"),
    path('games/story-telling/', story_telling_view, name='story-telling'),
    path('games/story-telling/<int:story_id>/<int:part_number>/', story_telling_view, name='story-telling-part'),

    path('games/', games_page_view, name="games"),
    path('multiple-choice/', multiple_choice_view, name='multiple-choice'),
    path('leaderboard/', leaderboard_view, name='leaderboard'),

    ### --------- Lecture Slides -------------- ###
    path('slides/', views.slide_view, name='slide_view'),
    path('slides/<int:slide_id>/', views.slide_view, name='view_slide'),
    path('slide/<int:slide_id>/submit-question/', views.submit_slide_question, name='submit_slide_question'), 

    path('add/levels/', views.manage_levels, name='manage_levels'),
    path('add/modules/<int:level_id>/', views.manage_modules, name='manage_modules'),
    path('add/slides/<int:module_id>/', views.manage_slides, name='manage_slides'),
    path('add/slide-content/<int:slide_id>/', views.create_slide_content, name='create_slide_content'),

    
    #tony
    path('letter-copy/', letter_copy_view, name='letter-copy'),
    path('letter-copy/<int:pk>/', letter_copy_view, name='letter-copy-with-pk'),
    path('match-and-write/', match_and_write, name='match-and-write'),
    path('reset-activity/', reset_activity, name='reset-activity'),
    path('letter-memory-game/', letter_memory_game, name='letter-memory-game'),
    path('sound-sorting/', sound_sorting, name='sound-sorting'),
    path('letter-sound-identification/', letter_sound_identification, name='letter-sound-identification'),
    path('sound-impitation/', sound_imitation, name='sound-imitation'),
    path('letter-hunt/', letter_hunt_view, name='letter-hunt'),
    path('letter-puzzles/', views.letter_puzzles, name='letter-puzzles'),
    path('tracing/', views.tracing_board, name='tracing-board'),
    path('letter-sound-identification/', views.letter_sound_identification, name='letter-sound-identification'),
    path('letter-dictation/', views.letter_dictation, name='letter-dictation'),
    path('bingo/', views.bingo_game, name='bingo-game'),
    path('check-answer/', views.check_answer, name='check-answer'),
    path('letter-sound-sequencing/', views.letter_sound_sequencing, name='letter-sound-sequencing'),

    path('remembering-game/', views.remembering_game, name='remembering-game'),
    path('descriptive-image-game/', views.descriptive_image_game, name='descriptive-image-game'),
    path('descriptive-sentence-game/', views.descriptive_sentence_game, name='descriptive-sentence-game'),
    path('word-copy-game/', views.word_copy_game, name='word-copy-game'),
    path('fill-in-the-blank/', views.fill_in_the_blank_game, name='fill-in-the-blank-game'), 
    path('number-to-word/', views.number_to_word_game, name='number-to-word_game'),
    path('writing-practice/', views.writing_practice, name='writing-practice'),
    path('video/', views.video_game, name='video-game'),  # For loading the first video
    path('video/<int:video_id>/', views.video_game, name='video-game-with_id'),  # For loading a specific video
    path('video/submit/<int:video_id>/', views.submit_video_response, name='submit-video-response'),
    path('word-audio/', views.word_audio_activity, name='word-audio-activity'),
    path('submit-word-audio/', views.submit_word_audio_recording, name='submit-word-audio-recording'),
    path('sentence-game/<int:sentence_id>/', views.sentence_audio_game, name='sentence-audio-game'), #access this page using /sentence-game/1/
    path('paragraph/', views.paragraph_game, name='paragraph-game'),  # This URL pattern points to the view for your paragraph game
    path('record_voice/', views.record_voice, name='record-voice'),
    path('voice_recording_success/', views.voice_recording_success, name='voice-recording-success'),  # Success page

    #custom admin
    path('custom-admin/', views.custom_admin_page, name='custom_admin_page'),
   # path('custom-admin/user-profiles/', views.user_profiles, name='user_profiles'),  # Add a path for user profiles
    path('custom-admin/events-admin/', views.event_page, name='events_page'),
    path('events/update/<int:event_id>/', views.update_event, name='update_event'),
    path('events/delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('custom-admin/lettersound-admin/', views.letter_sound_admin, name='letter_sound_admin'),
    path('custom-admin/word-audio-admin/', views.word_audio_admin, name='word_audio_admin'),
    path('custom-admin/word-video-admin/', views.word_video_admin, name='word_video_admin'),
    path('custom-admin/letter-video-admin/', views.letter_video_admin, name='letter_video_admin'),
    path('custom-admin/letter-image-admin/', views.letter_image_admin, name='letter_image_admin'),
    path('custom-admin/wordcountdown/', views.admin_wordcountdown, name='admin_wordcountdown'),
    path('custom-admin/sentences/', views.sentence_customadmin, name='sentence_customadmin'),
    path('custom-admin/passages/', views.passage_customadmin, name='passage_customadmin'),
    path('custom-admin/descriptive-images/', views.descriptive_image_customadmin, name='descriptive_image_customadmin'),
    path('custom-admin/descriptive-sentence-questions/', views.descriptive_sentence_question_customadmin, name='descriptive_sentence_question_customadmin'),
    path('custom-admin/fill-in-the-blank/', views.fill_in_the_blank_customadmin, name='fill_in_the_blank_customadmin'),
    path('custom-admin/numbers/', views.numbers_customadmin, name='numbers_customadmin'),
    path('custom-admin/writing-submissions/', views.writing_submission_customadmin, name='writing_submission_customadmin'),
    path('custom-admin/videos/', views.video_customadmin, name='video_customadmin'),
    path('custom-admin/video-responses/', views.video_response_customadmin, name='video_response_customadmin'),
    path('custom-admin/word-audio-recordings/', views.word_audio_recording_customadmin, name='word_audio_recording_customadmin'),
    path('custom-admin/paragraphs/', views.paragraph_customadmin, name='paragraph_customadmin'),
    path('custom-admin/voice-recordings/', views.voice_recording_customadmin, name='voice_recording_customadmin'),
    path('custom-admin/paragraph-creations/', views.paragraph_creation_customadmin, name='paragraph_creation_customadmin'),
    path('custom-admin/amharic-letter-families/', views.amharic_letter_family_customadmin, name='amharic_letter_family_customadmin'),
    path('custom-admin/amharic-letter-audios/', views.amharic_letter_audio_customadmin, name='amharic_letter_audio_customadmin'),
    path('custom-admin/letter-fill-ins/', views.letter_fill_in_customadmin, name='letter_fill_in_customadmin'),
    path('custom-admin/number-to-words/', views.number_to_word_customadmin, name='number_to_word_customadmin'),
    path('custom-admin/amharic-english-matching/', views.amharic_english_matching_customadmin, name='amharic_english_matching_customadmin'),
    path('custom-admin/sentence-synonyms/', views.sentence_synonym_customadmin, name='sentence_synonym_customadmin'),
    path('custom-admin/sentence-punctuation/', views.sentence_punctuation_customadmin, name='sentence_punctuation_customadmin'),
    path('custom-admin/stories/', views.story_customadmin, name='story_customadmin'),
    path('custom-admin/story-parts/', views.story_part_customadmin, name='story_part_customadmin'),
    path('custom-admin/story-questions/', views.story_question_customadmin, name='story_question_customadmin'),
    path('custom-admin/levels/', views.level_customadmin, name='level_customadmin'),
    path('custom-admin/modules/', views.module_customadmin, name='module_customadmin'),
    path('custom-admin/slides/', views.slide_customadmin, name='slide_customadmin'),
    path('custom-admin/slide-contents/', views.slide_content_customadmin, name='slide_content_customadmin'),
    path('custom-admin/slide-questions/', views.slide_question_customadmin, name='slide_question_customadmin'),
    path('custom-admin/user-slide-progress/', views.user_slide_progress_customadmin, name='user_slide_progress_customadmin'),
    path('custom-admin/user-level-progress/', views.user_level_progress_customadmin, name='user_level_progress_customadmin'),
    path('custom-admin/user-module-progress/', views.user_module_progress_customadmin, name='user_module_progress_customadmin'),
    path('custom-admin/user-profile/', views.user_profile_customadmin, name='user_profile_customadmin'),
    path('custom-admin/point-history/', views.point_history_customadmin, name='point_history_customadmin'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)