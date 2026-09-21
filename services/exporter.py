import json
import logging
import subprocess
import re

logger = logging.getLogger('stt-worker')

class ExporterService:
    def process(self, payload, redis_client, shutdown_event):
        export_id = payload.get('export_id')
        ffmpeg_cmd = payload.get('ffmpeg_cmd')
        output_path = payload.get('output_path')
        duration = float(payload.get('duration', 1.0))
        if duration <= 0:
            duration = 1.0
            
        logger.info(f"Processing export {export_id} (Duration: {duration}s)")
        
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                shell=True,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")
            last_progress = -1
            last_error_line = ""
            
            for line in process.stderr:
                if shutdown_event.is_set():
                    logger.info(f"Shutdown requested. Terminating export {export_id}...")
                    process.terminate()
                    break
                    
                match = time_regex.search(line)
                if match:
                    h, m, s = match.groups()
                    current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    progress = min(99, int((current_seconds / duration) * 100))
                    
                    if progress != last_progress:
                        redis_client.setex(f"laravel-database-export_progress_{export_id}", 3600, progress)
                        last_progress = progress
                else:
                    last_error_line = line.strip()
                        
            process.wait()
            
            if process.returncode == 0:
                redis_client.setex(f"laravel-database-export_progress_{export_id}", 3600, 100)
                success_payload = {
                    'status': 'success',
                    'export_id': export_id,
                    'output_path': output_path
                }
                redis_client.rpush('laravel-database-export_results', json.dumps(success_payload))
                logger.info(f"Successfully processed export {export_id}")
            elif not shutdown_event.is_set():
                error_msg = f"FFmpeg exited with code {process.returncode}. Stderr: {last_error_line}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error processing export {export_id}: {e}")
            error_payload = {
                'status': 'error',
                'export_id': export_id,
                'error': str(e)
            }
            redis_client.rpush('laravel-database-export_results', json.dumps(error_payload))
