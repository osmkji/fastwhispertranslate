import json
import logging
from app.transcriber import transcriber

logger = logging.getLogger('stt-worker')

class TranscriberService:
    def process(self, payload, redis_client):
        project_id = payload.get('project_id')
        job_id = payload.get('job_id')
        file_path = payload.get('file_path')
        
        logger.info(f"Processing transcription job {job_id} for project {project_id} (file: {file_path})")
        
        try:
            transcription_result = transcriber.transcribe(file_path)
            success_payload = {
                'status': 'success',
                'project_id': project_id,
                'job_id': job_id,
                'data': transcription_result
            }
            redis_client.rpush('laravel-database-transcription_results', json.dumps(success_payload))
            logger.info(f"Successfully processed and pushed result for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            error_payload = {
                'status': 'error',
                'project_id': project_id,
                'job_id': job_id,
                'error': str(e)
            }
            redis_client.rpush('laravel-database-transcription_results', json.dumps(error_payload))
