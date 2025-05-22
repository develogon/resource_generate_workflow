```mermaid
graph TB
    %% メインプロセス
    Start([開始]) --> RunScript[ローカルでCLI実行]
    RunScript --> CheckResumeFlag{再開フラグあり?}
    
    %% 処理再開フロー
    CheckResumeFlag -->|Yes| LoadCheckpoint[チェックポイントから状態復元]
    LoadCheckpoint --> ResumeProcess[実行中タスクから処理再開]
    ResumeProcess --> ExecuteTaskLoop
    
    %% 通常処理フロー
    CheckResumeFlag -->|No| FetchSource[til/go/タイトル名/text.mdを取得]
    FetchSource --> SplitChapters[text.mdを##でchapter分割]
    
    %% 初期チェックポイント処理
    SplitChapters --> RegisterInitialTasks[初期実行タスクを登録]
    RegisterInitialTasks --> SaveInitialCheckpoint[初期チェックポイント保存]
    SaveInitialCheckpoint --> ExecuteTaskLoop[タスク実行ループ]
    
    %% タスク実行管理
    ExecuteTaskLoop --> GetNextTask[次のタスクを取得]
    GetNextTask --> CheckTaskCompleted{タスク完了済み?}
    CheckTaskCompleted -->|Yes| SkipTask[タスクをスキップ]
    CheckTaskCompleted -->|No| ExecuteTask[タスクを実行]
    ExecuteTask --> UpdateProgress[進捗率を更新]
    UpdateProgress --> SaveTaskCheckpoint[タスク完了チェックポイント保存]
    SaveTaskCheckpoint --> CheckMoreTasks{残りタスクあり?}
    CheckMoreTasks -->|Yes| GetNextTask
    CheckMoreTasks -->|No| FinalizeProcess[処理完了]
    SkipTask --> CheckMoreTasks
    
    %% Chapter処理ループ
    SplitChapters --> ChapterLoop{各chapterごとの処理}
    ChapterLoop --> CreateChapterFolder[chapterフォルダ作成]
    CreateChapterFolder --> WriteChapterContent[text.mdにchapterコンテンツ書き込み]
    WriteChapterContent --> RegisterGitHubPushTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTask --> GitHubPushChapter[GitHubにpush]
    GitHubPushChapter --> SaveChapterCheckpoint[チャプター処理チェックポイント保存]
    SaveChapterCheckpoint --> SplitSections[text.mdを##, ###でsection分割]
    
    %% Section処理ループ
    SplitSections --> SectionLoop{各sectionごとの処理}
    SectionLoop --> CreateSectionFolder[sectionフォルダ作成]
    CreateSectionFolder --> WriteSectionContent[text.mdにsectionコンテンツ書き込み]
    WriteSectionContent --> RegisterGitHubPushSectionTask[GitHubプッシュタスク登録]
    RegisterGitHubPushSectionTask --> GitHubPushSection[GitHubにpush]
    GitHubPushSection --> SaveSectionCheckpoint[セクション処理チェックポイント保存]
    
    %% 画像処理フロー
    SectionLoop --> ProcessImages[埋め込まれた画像を処理]
    ProcessImages --> CheckHasImages{画像あり?}
    CheckHasImages -->|Yes| EncodeImages[Base64エンコード]
    EncodeImages --> ReplaceImageInMd[text.mdの画像部分を置換]
    ReplaceImageInMd --> RegisterGitHubPushImgTask[GitHubプッシュタスク登録]
    RegisterGitHubPushImgTask --> GitHubPushEncodedImg[GitHubにpush]
    CheckHasImages -->|No| SkipImageProcess[画像処理をスキップ]
    
    %% 段落構造作成
    SectionLoop --> CreateStructure[section_structure.yaml作成]
    CreateStructure --> PrepareClaudeReq[Claude API用リクエスト準備]
    PrepareClaudeReq --> CheckEncodedImages{エンコード画像あり?}
    CheckEncodedImages -->|Yes| IncludeImagesInPrompt[画像をプロンプトに含める]
    IncludeImagesInPrompt --> RegisterClaudeApiCall1[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall1 --> CallClaudeApi1[Claude APIを呼び出し]
    CheckEncodedImages -->|No| RegisterClaudeApiCall1
    CallClaudeApi1 --> ExtractYaml[YAMLを抽出]
    ExtractYaml --> WriteStructureYaml[section_structure.yamlに書き込み]
    WriteStructureYaml --> RegisterGitHubPushStructureTask[GitHubプッシュタスク登録]
    RegisterGitHubPushStructureTask --> GitHubPushStructure[GitHubにpush]
    GitHubPushStructure --> SaveStructureCheckpoint[構造作成チェックポイント保存]
    
    %% Paragraph処理ループ
    GitHubPushStructure --> ParagraphLoop{各paragraphごとの処理}
    
    %% 記事生成
    ParagraphLoop --> CreateArticle[article.md作成]
    CreateArticle --> GetArticlePrompt[article作成用プロンプト取得]
    GetArticlePrompt --> RegisterClaudeApiCall2[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall2 --> CallClaudeApi2[Claude APIを呼び出し]
    CallClaudeApi2 --> ExtractArticleMd[Markdownを抽出]
    ExtractArticleMd --> WriteArticleMd[article.mdに書き込み]
    WriteArticleMd --> RegisterGitHubPushArticleTask[GitHubプッシュタスク登録]
    RegisterGitHubPushArticleTask --> GitHubPushArticle[GitHubにpush]
    GitHubPushArticle --> SaveArticleCheckpoint[記事作成チェックポイント保存]
    
    %% 画像変換処理
    GitHubPushArticle --> CheckArticleImages{article.mdに画像あり?}
    CheckArticleImages -->|Yes| ProcessArticleImages[画像処理]
    ProcessArticleImages --> CheckImageType{画像タイプ?}
    CheckImageType -->|SVG| ProcessSvg[SVG処理]
    CheckImageType -->|DrawIO XML| ProcessDrawIO[DrawIO XML処理]
    CheckImageType -->|Mermaid| ProcessMermaid[Mermaid処理]
    
    %% SVG処理
    ProcessSvg --> ExtractSvg[SVG部分抽出]
    ExtractSvg --> ConvertSvgToPng[PNGに変換]
    ConvertSvgToPng --> SaveToImagesFolder1[imagesフォルダに保存]
    SaveToImagesFolder1 --> RegisterS3UploadTask1[S3アップロードタスク登録]
    RegisterS3UploadTask1 --> UploadToS31[S3にアップロード]
    UploadToS31 --> ReplaceWithLink1[画像リンクに置換]
    ReplaceWithLink1 --> RegisterGitHubPushImgTask1[GitHubプッシュタスク登録]
    RegisterGitHubPushImgTask1 --> GitHubPushImgProcessed1[GitHubにpush]
    GitHubPushImgProcessed1 --> SaveImageProcessedCheckpoint1[画像処理チェックポイント保存]
    
    %% DrawIO処理
    ProcessDrawIO --> ExtractXml[XML部分抽出]
    ExtractXml --> ConvertXmlToPng[PNGに変換]
    ConvertXmlToPng --> SaveToImagesFolder2[imagesフォルダに保存]
    SaveToImagesFolder2 --> RegisterS3UploadTask2[S3アップロードタスク登録]
    RegisterS3UploadTask2 --> UploadToS32[S3にアップロード]
    UploadToS32 --> ReplaceWithLink2[画像リンクに置換]
    ReplaceWithLink2 --> RegisterGitHubPushImgTask2[GitHubプッシュタスク登録]
    RegisterGitHubPushImgTask2 --> GitHubPushImgProcessed2[GitHubにpush]
    GitHubPushImgProcessed2 --> SaveImageProcessedCheckpoint2[画像処理チェックポイント保存]
    
    %% Mermaid処理
    ProcessMermaid --> ExtractMermaid[Mermaid部分抽出]
    ExtractMermaid --> ConvertMermaidToPng[PNGに変換]
    ConvertMermaidToPng --> SaveToImagesFolder3[imagesフォルダに保存]
    SaveToImagesFolder3 --> RegisterS3UploadTask3[S3アップロードタスク登録]
    RegisterS3UploadTask3 --> UploadToS33[S3にアップロード]
    UploadToS33 --> ReplaceWithLink3[画像リンクに置換]
    ReplaceWithLink3 --> RegisterGitHubPushImgTask3[GitHubプッシュタスク登録]
    RegisterGitHubPushImgTask3 --> GitHubPushImgProcessed3[GitHubにpush]
    GitHubPushImgProcessed3 --> SaveImageProcessedCheckpoint3[画像処理チェックポイント保存]
    
    %% 台本作成
    ParagraphLoop --> CreateScript[script.md作成]
    CreateScript --> GetScriptPrompt[script作成用プロンプト取得]
    GetScriptPrompt --> RegisterClaudeApiCall3[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall3 --> CallClaudeApi3[Claude APIを呼び出し]
    CallClaudeApi3 --> ExtractScriptMd[Markdownを抽出]
    ExtractScriptMd --> WriteScriptMd[script.mdに書き込み]
    WriteScriptMd --> RegisterGitHubPushScriptTask[GitHubプッシュタスク登録]
    RegisterGitHubPushScriptTask --> GitHubPushScript[GitHubにpush]
    GitHubPushScript --> SaveScriptCheckpoint[台本作成チェックポイント保存]
    
    %% 台本JSON作成
    ParagraphLoop --> CreateScriptJson[script.json作成]
    CreateScriptJson --> GetScriptJsonPrompt[script.json作成用プロンプト取得]
    GetScriptJsonPrompt --> RegisterClaudeApiCall4[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall4 --> CallClaudeApi4[Claude APIを呼び出し]
    CallClaudeApi4 --> ExtractScriptJson[JSONを抽出]
    ExtractScriptJson --> WriteScriptJson[script.jsonに書き込み]
    WriteScriptJson --> RegisterGitHubPushScriptJsonTask[GitHubプッシュタスク登録]
    RegisterGitHubPushScriptJsonTask --> GitHubPushScriptJson[GitHubにpush]
    GitHubPushScriptJson --> SaveScriptJsonCheckpoint[台本JSON作成チェックポイント保存]
    
    %% ツイート作成
    ParagraphLoop --> CreateTweets[tweets.csv作成]
    CreateTweets --> GetTweetsPrompt[tweets作成用プロンプト取得]
    GetTweetsPrompt --> RegisterClaudeApiCall5[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall5 --> CallClaudeApi5[Claude APIを呼び出し]
    CallClaudeApi5 --> ExtractTweetsCsv[CSVを抽出]
    ExtractTweetsCsv --> WriteTweetsCsv[tweets.csvに書き込み]
    WriteTweetsCsv --> RegisterGitHubPushTweetsTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTweetsTask --> GitHubPushTweets[GitHubにpush]
    GitHubPushTweets --> SaveTweetsCheckpoint[ツイート作成チェックポイント保存]
    
    %% Sectionのコンテンツ結合
    SectionLoop --> EndSectionProcess[section処理完了]
    EndSectionProcess --> CombineSectionContents[sectionのコンテンツ結合]
    CombineSectionContents --> SaveSectionCombineCheckpoint[セクション結合チェックポイント保存]
    
    %% Combined files
    CombineSectionContents --> CombineSectionArticles[各sectionのarticle.mdを結合]
    CombineSectionContents --> CombineSectionScripts[各sectionのscript.mdを結合]
    CombineSectionContents --> CombineSectionScriptJSONs[各sectionのscript.jsonを結合]
    CombineSectionContents --> CombineSectionTweets[各sectionのtweets.csvを結合]
    CombineSectionContents --> CombineSectionImages[各sectionのimagesフォルダを結合]
    
    %% GitHub Push
    CombineSectionArticles --> RegisterGitHubPushCombinedArticleTask[GitHubプッシュタスク登録]
    RegisterGitHubPushCombinedArticleTask --> GitHubPushCombinedArticle[GitHubにpush]
    CombineSectionScripts --> RegisterGitHubPushCombinedScriptTask[GitHubプッシュタスク登録]
    RegisterGitHubPushCombinedScriptTask --> GitHubPushCombinedScript[GitHubにpush]
    CombineSectionScriptJSONs --> RegisterGitHubPushCombinedJsonTask[GitHubプッシュタスク登録]
    RegisterGitHubPushCombinedJsonTask --> GitHubPushCombinedJson[GitHubにpush]
    CombineSectionTweets --> RegisterGitHubPushCombinedTweetsTask[GitHubプッシュタスク登録]
    RegisterGitHubPushCombinedTweetsTask --> GitHubPushCombinedTweets[GitHubにpush]
    CombineSectionImages --> RegisterGitHubPushCombinedImagesTask[GitHubプッシュタスク登録]
    RegisterGitHubPushCombinedImagesTask --> GitHubPushCombinedImages[GitHubにpush]
    
    %% Chapterのコンテンツ結合
    ChapterLoop --> EndChapterProcess[chapter処理完了]
    EndChapterProcess --> CombineChapterContents[chapterのコンテンツ結合]
    CombineChapterContents --> SaveChapterCombineCheckpoint[チャプター結合チェックポイント保存]
    
    %% Combined files at title level
    CombineChapterContents --> CombineChapterArticles[各chapterのarticle.mdを結合]
    CombineChapterContents --> CombineChapterScripts[各chapterのscript.mdを結合]
    CombineChapterContents --> CombineChapterTweets[各chapterのtweets.csvを結合]
    CombineChapterContents --> CombineChapterImages[各chapterのimagesフォルダを結合]
    
    %% GitHub Push 
    CombineChapterArticles --> RegisterGitHubPushTitleArticleTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTitleArticleTask --> GitHubPushTitleArticle[GitHubにpush]
    CombineChapterScripts --> RegisterGitHubPushTitleScriptTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTitleScriptTask --> GitHubPushTitleScript[GitHubにpush]
    CombineChapterTweets --> RegisterGitHubPushTitleTweetsTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTitleTweetsTask --> GitHubPushTitleTweets[GitHubにpush]
    CombineChapterImages --> RegisterGitHubPushTitleImagesTask[GitHubプッシュタスク登録]
    RegisterGitHubPushTitleImagesTask --> GitHubPushTitleImages[GitHubにpush]
    
    %% 構造ファイル作成
    GitHubPushTitleArticle --> CreateStructureMd[article.mdから見出しを抽出しstructure.md作成]
    CreateStructureMd --> WriteStructureMd[structure.mdに書き込み]
    WriteStructureMd --> RegisterGitHubPushStructureMdTask[GitHubプッシュタスク登録]
    RegisterGitHubPushStructureMdTask --> GitHubPushStructureMd[GitHubにpush]
    GitHubPushStructureMd --> SaveStructureMdCheckpoint[構造ファイルチェックポイント保存]
    
    %% Description作成
    GitHubPushStructureMd --> CreateDescription[description作成]
    CreateDescription --> GetDescriptionPrompt[description用プロンプト取得]
    GetDescriptionPrompt --> RegisterClaudeApiCall6[Claude API呼び出しタスク登録]
    RegisterClaudeApiCall6 --> CallClaudeApi6[Claude APIを呼び出し]
    CallClaudeApi6 --> ExtractDescriptionMd[Markdownを抽出]
    ExtractDescriptionMd --> WriteDescriptionMd[description.mdに書き込み]
    WriteDescriptionMd --> AppendDescriptionTemplate[説明文テンプレートを追記]
    AppendDescriptionTemplate --> RegisterGitHubPushDescriptionTask[GitHubプッシュタスク登録]
    RegisterGitHubPushDescriptionTask --> GitHubPushDescription[GitHubにpush]
    GitHubPushDescription --> SaveDescriptionCheckpoint[説明文作成チェックポイント保存]

    %% Thumbnail作成
    GitHubPushStructureMd --> CreateThumbnail[thumbnail作成]
    CreateThumbnail --> ReadDescriptionMd[description.mdを読み込み]
    ReadDescriptionMd --> LoadTemplateYaml[thumbnail_template.yamlを読み込み]
    LoadTemplateYaml --> RegisterOpenAIGPT4Call[OpenAI GPT-4o-mini呼び出しタスク登録]
    RegisterOpenAIGPT4Call --> CallOpenAIGPT4[OpenAI GPT-4o-miniを呼び出し]
    CallOpenAIGPT4 --> OptimizeTemplate[YAMLテンプレート最適化]
    OptimizeTemplate --> RegisterOpenAIImageCall[OpenAI画像生成APIタスク登録]
    RegisterOpenAIImageCall --> CallOpenAIImage[OpenAI GPT-Image-1呼び出し]
    CallOpenAIImage --> SaveThumbnailImage[thumbnailフォルダに画像保存]
    SaveThumbnailImage --> LogAPIUsage[API使用状況をログ記録]
    LogAPIUsage --> RegisterS3UploadThumbnailTask[S3アップロードタスク登録]
    RegisterS3UploadThumbnailTask --> UploadThumbnailToS3[サムネイルをS3にアップロード]
    UploadThumbnailToS3 --> RegisterGitHubPushThumbnailTask[GitHubプッシュタスク登録]
    RegisterGitHubPushThumbnailTask --> GitHubPushThumbnail[GitHubにpush]
    GitHubPushThumbnail --> SaveThumbnailCheckpoint[サムネイル作成チェックポイント保存]
    
    %% 完了通知（Description処理とThumbnail処理が両方完了した後）
    GitHubPushDescription --> CheckAllProcessed{全処理完了?}
    GitHubPushThumbnail --> CheckAllProcessed
    CheckAllProcessed -->|Yes| NotifySlack[Slackで完了通知]
    
    %% エラー処理
    RunScript --> ErrorHandler{エラー発生?}
    ErrorHandler -->|Yes| SaveErrorCheckpoint[エラーチェックポイント保存]
    SaveErrorCheckpoint --> NotifySlackError[Slackでエラー通知]
    ErrorHandler -->|No| ContinueProcess[処理継続]
    
    %% 入力パスオプション処理
    FetchSource --> CheckInputPath{入力パス指定あり?}
    CheckInputPath -->|Yes| UseSpecifiedPath[指定パスを使用]
    CheckInputPath -->|No| UseDefaultPath[デフォルトパスを使用]
    UseSpecifiedPath --> SplitChapters
    UseDefaultPath --> SplitChapters
    
    %% スタイル
    classDef api fill:#f9a,stroke:#333,stroke-width:2px;
    classDef github fill:#9af,stroke:#333,stroke-width:2px;
    classDef process fill:#9f9,stroke:#333,stroke-width:2px;
    classDef decision fill:#ff9,stroke:#333,stroke-width:2px;
    classDef start fill:#f99,stroke:#333,stroke-width:2px;
    classDef checkpoint fill:#a6f,stroke:#333,stroke-width:2px;
    classDef register fill:#fa6,stroke:#333,stroke-width:2px;
    classDef openai fill:#fcb,stroke:#333,stroke-width:2px;
    
    class CallClaudeApi1,CallClaudeApi2,CallClaudeApi3,CallClaudeApi4,CallClaudeApi5,CallClaudeApi6 api;
    class CallOpenAIGPT4,CallOpenAIImage openai;
    class GitHubPushChapter,GitHubPushSection,GitHubPushEncodedImg,GitHubPushStructure,GitHubPushArticle,GitHubPushImgProcessed1,GitHubPushImgProcessed2,GitHubPushImgProcessed3,GitHubPushScript,GitHubPushScriptJson,GitHubPushTweets,GitHubPushCombinedArticle,GitHubPushCombinedScript,GitHubPushCombinedJson,GitHubPushCombinedTweets,GitHubPushCombinedImages,GitHubPushTitleArticle,GitHubPushTitleScript,GitHubPushTitleTweets,GitHubPushTitleImages,GitHubPushStructureMd,GitHubPushDescription,GitHubPushThumbnail github;
    class SplitChapters,CreateChapterFolder,WriteChapterContent,SplitSections,CreateSectionFolder,WriteSectionContent,ProcessImages,EncodeImages,ReplaceImageInMd,CreateStructure,PrepareClaudeReq,ExtractYaml,WriteStructureYaml,CreateArticle,GetArticlePrompt,ExtractArticleMd,WriteArticleMd,ProcessArticleImages,ExtractSvg,ConvertSvgToPng,SaveToImagesFolder1,UploadToS31,ReplaceWithLink1,ExtractXml,ConvertXmlToPng,SaveToImagesFolder2,UploadToS32,ReplaceWithLink2,ExtractMermaid,ConvertMermaidToPng,SaveToImagesFolder3,UploadToS33,ReplaceWithLink3,CreateScript,GetScriptPrompt,ExtractScriptMd,WriteScriptMd,CreateScriptJson,GetScriptJsonPrompt,ExtractScriptJson,WriteScriptJson,CreateTweets,GetTweetsPrompt,ExtractTweetsCsv,WriteTweetsCsv,CombineSectionContents,CombineSectionArticles,CombineSectionScripts,CombineSectionScriptJSONs,CombineSectionTweets,CombineSectionImages,CombineChapterContents,CombineChapterArticles,CombineChapterScripts,CombineChapterTweets,CombineChapterImages,CreateStructureMd,WriteStructureMd,CreateDescription,GetDescriptionPrompt,ExtractDescriptionMd,WriteDescriptionMd,AppendDescriptionTemplate,CreateThumbnail,ReadDescriptionMd,LoadTemplateYaml,OptimizeTemplate,SaveThumbnailImage,LogAPIUsage,UploadThumbnailToS3,ExecuteTask,UpdateProgress,SkipTask,GetNextTask,ResumeProcess,FinalizeProcess,UseSpecifiedPath,UseDefaultPath process;
    class ChapterLoop,SectionLoop,CheckHasImages,CheckEncodedImages,ParagraphLoop,CheckArticleImages,CheckImageType,ErrorHandler,CheckResumeFlag,CheckTaskCompleted,CheckMoreTasks,CheckInputPath,CheckAllProcessed decision;
    class Start,NotifySlack,NotifySlackError start;
    class SaveInitialCheckpoint,SaveChapterCheckpoint,SaveSectionCheckpoint,SaveStructureCheckpoint,SaveArticleCheckpoint,SaveImageProcessedCheckpoint1,SaveImageProcessedCheckpoint2,SaveImageProcessedCheckpoint3,SaveScriptCheckpoint,SaveScriptJsonCheckpoint,SaveTweetsCheckpoint,SaveSectionCombineCheckpoint,SaveChapterCombineCheckpoint,SaveStructureMdCheckpoint,SaveDescriptionCheckpoint,SaveThumbnailCheckpoint,SaveErrorCheckpoint,SaveTaskCheckpoint,LoadCheckpoint checkpoint;
    class RegisterInitialTasks,RegisterGitHubPushTask,RegisterGitHubPushSectionTask,RegisterGitHubPushImgTask,RegisterClaudeApiCall1,RegisterGitHubPushStructureTask,RegisterClaudeApiCall2,RegisterGitHubPushArticleTask,RegisterS3UploadTask1,RegisterGitHubPushImgTask1,RegisterS3UploadTask2,RegisterGitHubPushImgTask2,RegisterS3UploadTask3,RegisterGitHubPushImgTask3,RegisterClaudeApiCall3,RegisterGitHubPushScriptTask,RegisterClaudeApiCall4,RegisterGitHubPushScriptJsonTask,RegisterClaudeApiCall5,RegisterGitHubPushTweetsTask,RegisterGitHubPushCombinedArticleTask,RegisterGitHubPushCombinedScriptTask,RegisterGitHubPushCombinedJsonTask,RegisterGitHubPushCombinedTweetsTask,RegisterGitHubPushCombinedImagesTask,RegisterGitHubPushTitleArticleTask,RegisterGitHubPushTitleScriptTask,RegisterGitHubPushTitleTweetsTask,RegisterGitHubPushTitleImagesTask,RegisterGitHubPushStructureMdTask,RegisterClaudeApiCall6,RegisterGitHubPushDescriptionTask,RegisterOpenAIGPT4Call,RegisterOpenAIImageCall,RegisterS3UploadThumbnailTask,RegisterGitHubPushThumbnailTask register;
```