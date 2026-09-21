import json
import logging

logger = logging.getLogger('stt-worker')

class TranslatorService:
    def __init__(self):
        self.translator = None
        self.tokenizer = None
        self.NLLB_LANGUAGES = {
            'en': 'eng_Latn', 'es': 'spa_Latn', 'fr': 'fra_Latn', 'de': 'deu_Latn',
            'it': 'ita_Latn', 'pt': 'por_Latn', 'nl': 'nld_Latn', 'pl': 'pol_Latn',
            'ru': 'rus_Cyrl', 'ar': 'arb_Arab', 'zh-CN': 'zho_Hans', 'ja': 'jpn_Jpan',
            'ko': 'kor_Hang'
        }
        self._load_model()

    def _load_model(self):
        import ctranslate2
        import transformers
        logger.info("Loading NLLB-200 translation model into memory...")
        try:
            self.translator = ctranslate2.Translator("nllb-200-distilled-600M-ct2", device="cpu")
            self.tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
            logger.info("Translation model loaded successfully.")
        except Exception as e:
            logger.warning(f"Translation model failed to load. Translations will fail. Error: {e}")

    def process(self, payload, redis_client):
        project_id = payload.get('project_id')
        job_id = payload.get('job_id')
        target_language = payload.get('target_language', 'en')
        subtitles = payload.get('subtitles', [])
        
        logger.info(f"Processing translation job {job_id} for project {project_id} (target: {target_language})")
        
        try:
            if not self.translator or not self.tokenizer:
                raise Exception("Offline translation model is not loaded.")
                
            target_lang_nllb = self.NLLB_LANGUAGES.get(target_language, 'eng_Latn')
            texts_to_translate = [seg.get('text') or seg.get('word') or '' for seg in subtitles]
            translated_texts = []
            
            if texts_to_translate:
                self.tokenizer.src_lang = 'eng_Latn'
                source_tokens = [self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(t)) if t else [] for t in texts_to_translate]
                target_prefix = [[target_lang_nllb]] * len(source_tokens)
                
                valid_indices = [i for i, tokens in enumerate(source_tokens) if tokens]
                valid_source_tokens = [source_tokens[i] for i in valid_indices]
                valid_target_prefix = [target_prefix[i] for i in valid_indices]
                
                translated_texts = [''] * len(texts_to_translate)
                
                if valid_source_tokens:
                    results = self.translator.translate_batch(valid_source_tokens, target_prefix=valid_target_prefix)
                    for idx, result in zip(valid_indices, results):
                        target_tokens = result.hypotheses[0][1:]
                        translated_text = self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target_tokens))
                        translated_texts[idx] = translated_text
            
            translated_segments = []
            for i, seg in enumerate(subtitles):
                new_seg = {
                    'start': seg.get('start_time', seg.get('start', 0)),
                    'end': seg.get('end_time', seg.get('end', 0)),
                    'text': translated_texts[i] if i < len(translated_texts) else (seg.get('text') or ''),
                    'words': []
                }
                translated_segments.append(new_seg)
                
            success_payload = {
                'status': 'success',
                'project_id': project_id,
                'job_id': job_id,
                'data': {
                    'language': target_language,
                    'segments': translated_segments
                }
            }
            redis_client.rpush('laravel-database-transcription_results', json.dumps(success_payload))
            logger.info(f"Successfully processed and pushed translation result for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing translation job {job_id}: {e}")
            error_payload = {
                'status': 'error',
                'project_id': project_id,
                'job_id': job_id,
                'error': str(e)
            }
            redis_client.rpush('laravel-database-transcription_results', json.dumps(error_payload))
