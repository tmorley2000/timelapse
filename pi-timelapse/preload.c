#define _GNU_SOURCE
#include "interface/mmal/mmal.h"
#include "interface/mmal/mmal_logging.h"
#include "interface/mmal/mmal_buffer.h"
#include "interface/mmal/util/mmal_util.h"
#include "interface/mmal/util/mmal_util_params.h"
#include "interface/mmal/util/mmal_default_components.h"
#include "interface/mmal/util/mmal_connection.h"
#include "interface/mmal/mmal_parameters_camera.h"

#include <stdio.h>
#include <dlfcn.h>

struct namelist_t { char *name; void *thing; struct namelist_t *next; };

struct namelist_t *namelist=NULL;

void addname(char * name, void *thing)
{
 struct namelist_t *newname=malloc(sizeof(struct namelist_t));
 newname->name=malloc(strlen(name)+1);
 strcpy(newname->name,name);
 newname->thing=thing;
 newname->next=namelist;
 namelist=newname;
}

char *getname(void *thing)
{
 struct namelist_t *p=namelist;
 while (p!=NULL)
 {
  if(thing==p->thing)
   return p->name;
  p=p->next;
 }
 return NULL;
}

char *idtos(int id)
{
 char *p;
 switch(id)
 {
   case MMAL_PARAMETER_ZERO_COPY: return "MMAL_PARAMETER_ZERO_COPY";
   case MMAL_PARAMETER_THUMBNAIL_CONFIGURATION: return "MMAL_PARAMETER_THUMBNAIL_CONFIGURATION";
   case MMAL_PARAMETER_CAPTURE_QUALITY: return "MMAL_PARAMETER_CAPTURE_QUALITY";
   case MMAL_PARAMETER_ROTATION: return "MMAL_PARAMETER_ROTATION";
   case MMAL_PARAMETER_EXIF_DISABLE: return "MMAL_PARAMETER_EXIF_DISABLE";
   case MMAL_PARAMETER_EXIF: return "MMAL_PARAMETER_EXIF";
   case MMAL_PARAMETER_AWB_MODE: return "MMAL_PARAMETER_AWB_MODE";
   case MMAL_PARAMETER_IMAGE_EFFECT: return "MMAL_PARAMETER_IMAGE_EFFECT";
   case MMAL_PARAMETER_COLOUR_EFFECT: return "MMAL_PARAMETER_COLOUR_EFFECT";
   case MMAL_PARAMETER_FLICKER_AVOID: return "MMAL_PARAMETER_FLICKER_AVOID";
   case MMAL_PARAMETER_FLASH: return "MMAL_PARAMETER_FLASH";
   case MMAL_PARAMETER_REDEYE: return "MMAL_PARAMETER_REDEYE";
   case MMAL_PARAMETER_FOCUS: return "MMAL_PARAMETER_FOCUS";
   case MMAL_PARAMETER_FOCAL_LENGTHS: return "MMAL_PARAMETER_FOCAL_LENGTHS";
   case MMAL_PARAMETER_EXPOSURE_COMP: return "MMAL_PARAMETER_EXPOSURE_COMP";
   case MMAL_PARAMETER_ZOOM: return "MMAL_PARAMETER_ZOOM";
   case MMAL_PARAMETER_MIRROR: return "MMAL_PARAMETER_MIRROR";
   case MMAL_PARAMETER_CAMERA_NUM: return "MMAL_PARAMETER_CAMERA_NUM";
   case MMAL_PARAMETER_CAPTURE: return "MMAL_PARAMETER_CAPTURE";
   case MMAL_PARAMETER_EXPOSURE_MODE: return "MMAL_PARAMETER_EXPOSURE_MODE";
   case MMAL_PARAMETER_EXP_METERING_MODE: return "MMAL_PARAMETER_EXP_METERING_MODE";
   case MMAL_PARAMETER_FOCUS_STATUS: return "MMAL_PARAMETER_FOCUS_STATUS";
   case MMAL_PARAMETER_CAMERA_CONFIG: return "MMAL_PARAMETER_CAMERA_CONFIG";
   case MMAL_PARAMETER_CAPTURE_STATUS: return "MMAL_PARAMETER_CAPTURE_STATUS";
   case MMAL_PARAMETER_FACE_TRACK: return "MMAL_PARAMETER_FACE_TRACK";
   case MMAL_PARAMETER_DRAW_BOX_FACES_AND_FOCUS: return "MMAL_PARAMETER_DRAW_BOX_FACES_AND_FOCUS";
   case MMAL_PARAMETER_JPEG_Q_FACTOR: return "MMAL_PARAMETER_JPEG_Q_FACTOR";
   case MMAL_PARAMETER_FRAME_RATE: return "MMAL_PARAMETER_FRAME_RATE";
   case MMAL_PARAMETER_USE_STC: return "MMAL_PARAMETER_USE_STC";
   case MMAL_PARAMETER_CAMERA_INFO: return "MMAL_PARAMETER_CAMERA_INFO";
   case MMAL_PARAMETER_VIDEO_STABILISATION: return "MMAL_PARAMETER_VIDEO_STABILISATION";
   case MMAL_PARAMETER_FACE_TRACK_RESULTS: return "MMAL_PARAMETER_FACE_TRACK_RESULTS";
   case MMAL_PARAMETER_ENABLE_RAW_CAPTURE: return "MMAL_PARAMETER_ENABLE_RAW_CAPTURE";
   case MMAL_PARAMETER_DPF_FILE: return "MMAL_PARAMETER_DPF_FILE";
   case MMAL_PARAMETER_ENABLE_DPF_FILE: return "MMAL_PARAMETER_ENABLE_DPF_FILE";
   case MMAL_PARAMETER_DPF_FAIL_IS_FATAL: return "MMAL_PARAMETER_DPF_FAIL_IS_FATAL";
   case MMAL_PARAMETER_CAPTURE_MODE: return "MMAL_PARAMETER_CAPTURE_MODE";
   case MMAL_PARAMETER_FOCUS_REGIONS: return "MMAL_PARAMETER_FOCUS_REGIONS";
   case MMAL_PARAMETER_INPUT_CROP: return "MMAL_PARAMETER_INPUT_CROP";
   case MMAL_PARAMETER_SENSOR_INFORMATION: return "MMAL_PARAMETER_SENSOR_INFORMATION";
   case MMAL_PARAMETER_FLASH_SELECT: return "MMAL_PARAMETER_FLASH_SELECT";
   case MMAL_PARAMETER_FIELD_OF_VIEW: return "MMAL_PARAMETER_FIELD_OF_VIEW";
   case MMAL_PARAMETER_HIGH_DYNAMIC_RANGE: return "MMAL_PARAMETER_HIGH_DYNAMIC_RANGE";
   case MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION: return "MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION";
   case MMAL_PARAMETER_ALGORITHM_CONTROL: return "MMAL_PARAMETER_ALGORITHM_CONTROL";
   case MMAL_PARAMETER_SHARPNESS: return "MMAL_PARAMETER_SHARPNESS";
   case MMAL_PARAMETER_CONTRAST: return "MMAL_PARAMETER_CONTRAST";
   case MMAL_PARAMETER_BRIGHTNESS: return "MMAL_PARAMETER_BRIGHTNESS";
   case MMAL_PARAMETER_SATURATION: return "MMAL_PARAMETER_SATURATION";
   case MMAL_PARAMETER_ISO: return "MMAL_PARAMETER_ISO";
   case MMAL_PARAMETER_ANTISHAKE: return "MMAL_PARAMETER_ANTISHAKE";
   case MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS: return "MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS";
   case MMAL_PARAMETER_CAMERA_BURST_CAPTURE: return "MMAL_PARAMETER_CAMERA_BURST_CAPTURE";
   case MMAL_PARAMETER_CAMERA_MIN_ISO: return "MMAL_PARAMETER_CAMERA_MIN_ISO";
   case MMAL_PARAMETER_CAMERA_USE_CASE: return "MMAL_PARAMETER_CAMERA_USE_CASE";
   case MMAL_PARAMETER_CAPTURE_STATS_PASS: return "MMAL_PARAMETER_CAPTURE_STATS_PASS";
   case MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG: return "MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG";
   case MMAL_PARAMETER_ENABLE_REGISTER_FILE: return "MMAL_PARAMETER_ENABLE_REGISTER_FILE";
   case MMAL_PARAMETER_REGISTER_FAIL_IS_FATAL: return "MMAL_PARAMETER_REGISTER_FAIL_IS_FATAL";
   case MMAL_PARAMETER_CONFIGFILE_REGISTERS: return "MMAL_PARAMETER_CONFIGFILE_REGISTERS";
   case MMAL_PARAMETER_CONFIGFILE_CHUNK_REGISTERS: return "MMAL_PARAMETER_CONFIGFILE_CHUNK_REGISTERS";
   case MMAL_PARAMETER_JPEG_ATTACH_LOG: return "MMAL_PARAMETER_JPEG_ATTACH_LOG";
   case MMAL_PARAMETER_ZERO_SHUTTER_LAG: return "MMAL_PARAMETER_ZERO_SHUTTER_LAG";
   case MMAL_PARAMETER_FPS_RANGE: return "MMAL_PARAMETER_FPS_RANGE";
   case MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP: return "MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP";
   case MMAL_PARAMETER_SW_SHARPEN_DISABLE: return "MMAL_PARAMETER_SW_SHARPEN_DISABLE";
   case MMAL_PARAMETER_FLASH_REQUIRED: return "MMAL_PARAMETER_FLASH_REQUIRED";
   case MMAL_PARAMETER_SW_SATURATION_DISABLE: return "MMAL_PARAMETER_SW_SATURATION_DISABLE";
   case MMAL_PARAMETER_SHUTTER_SPEED: return "MMAL_PARAMETER_SHUTTER_SPEED";
   case MMAL_PARAMETER_CUSTOM_AWB_GAINS: return "MMAL_PARAMETER_CUSTOM_AWB_GAINS";
   case MMAL_PARAMETER_CAMERA_SETTINGS: return "MMAL_PARAMETER_CAMERA_SETTINGS";
   case MMAL_PARAMETER_PRIVACY_INDICATOR: return "MMAL_PARAMETER_PRIVACY_INDICATOR";
   case MMAL_PARAMETER_VIDEO_DENOISE: return "MMAL_PARAMETER_VIDEO_DENOISE";
   case MMAL_PARAMETER_STILLS_DENOISE: return "MMAL_PARAMETER_STILLS_DENOISE";
   case MMAL_PARAMETER_ANNOTATE: return "MMAL_PARAMETER_ANNOTATE";
   case MMAL_PARAMETER_STEREOSCOPIC_MODE: return "MMAL_PARAMETER_STEREOSCOPIC_MODE";
   case MMAL_PARAMETER_CAMERA_INTERFACE: return "MMAL_PARAMETER_CAMERA_INTERFACE";
   case MMAL_PARAMETER_CAMERA_CLOCKING_MODE: return "MMAL_PARAMETER_CAMERA_CLOCKING_MODE";
   case MMAL_PARAMETER_CAMERA_RX_CONFIG: return "MMAL_PARAMETER_CAMERA_RX_CONFIG";
   case MMAL_PARAMETER_CAMERA_RX_TIMING: return "MMAL_PARAMETER_CAMERA_RX_TIMING";
   case MMAL_PARAMETER_DPF_CONFIG: return "MMAL_PARAMETER_DPF_CONFIG";
   case MMAL_PARAMETER_JPEG_RESTART_INTERVAL: return "MMAL_PARAMETER_JPEG_RESTART_INTERVAL";
   case MMAL_PARAMETER_CAMERA_ISP_BLOCK_OVERRIDE: return "MMAL_PARAMETER_CAMERA_ISP_BLOCK_OVERRIDE";
   case MMAL_PARAMETER_LENS_SHADING_OVERRIDE: return "MMAL_PARAMETER_LENS_SHADING_OVERRIDE";
   case MMAL_PARAMETER_BLACK_LEVEL: return "MMAL_PARAMETER_BLACK_LEVEL";
   case MMAL_PARAMETER_RESIZE_PARAMS: return "MMAL_PARAMETER_RESIZE_PARAMS";
   case MMAL_PARAMETER_CROP: return "MMAL_PARAMETER_CROP";
   case MMAL_PARAMETER_OUTPUT_SHIFT: return "MMAL_PARAMETER_OUTPUT_SHIFT";
   case MMAL_PARAMETER_CCM_SHIFT: return "MMAL_PARAMETER_CCM_SHIFT";
   case MMAL_PARAMETER_CUSTOM_CCM: return "MMAL_PARAMETER_CUSTOM_CCM";
   case MMAL_PARAMETER_ANALOG_GAIN: return "MMAL_PARAMETER_ANALOG_GAIN";
   case MMAL_PARAMETER_DIGITAL_GAIN: return "MMAL_PARAMETER_DIGITAL_GAIN";
   default: p=malloc(100); sprintf(p,"unknown (%d)",id);return p;
 }
}

void decode_param(int id)
{
 printf("+           param=%s\n",idtos(id));
}

void decode_param_pack(const MMAL_PARAMETER_HEADER_T *param)
{
 MMAL_PARAMETER_CAMERA_CONFIG_T *p;
 switch(param->id)
 {
  case MMAL_PARAMETER_AWB_MODE:
       printf("+           awb_mode=%d\n",((MMAL_PARAMETER_AWBMODE_T *)param)->value);
       break;
  case MMAL_PARAMETER_BRIGHTNESS:
       printf("+           birghtness=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_CAMERA_CONFIG:
       p=((MMAL_PARAMETER_CAMERA_CONFIG_T *)param);
       printf("+           max_stills_w=%d\n",p->max_stills_w);
       printf("+           max_stills_h=%d\n",p->max_stills_h);
       printf("+           stills_yuv422=%d\n",p->stills_yuv422);
       printf("+           one_shot_stills=%d\n",p->one_shot_stills);
       printf("+           max_preview_video_w=%d\n",p->max_preview_video_w);
       printf("+           max_preview_video_h=%d\n",p->max_preview_video_h);
       printf("+           num_preview_video_frames=%d\n",p->num_preview_video_frames);
       printf("+           stills_capture_circular_buffer_height=%d\n",p->stills_capture_circular_buffer_height);
       printf("+           fast_preview_resume=%d\n",p->fast_preview_resume);

       break;
  case MMAL_PARAMETER_ZERO_COPY:
       printf("+           zero_copy=%d\n",((MMAL_PARAMETER_BOOLEAN_T *)param)->enable);
       break;
  case MMAL_PARAMETER_CAPTURE:
       printf("+           capture=%d\n",((MMAL_PARAMETER_BOOLEAN_T *)param)->enable);
       break;
  case MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP:
       printf("+           capture_exposure_comp=%d\n",((MMAL_PARAMETER_INT32_T *)param)->value);
       break;
  case MMAL_PARAMETER_CAPTURE_MODE:
       printf("+           capture_mode=%d\n",((MMAL_PARAMETER_CAPTUREMODE_T   *)param)->mode);
       break;
  case MMAL_PARAMETER_CUSTOM_AWB_GAINS:
       printf("+           awb_gains=%d/%d , %d/%d\n",((MMAL_PARAMETER_AWB_GAINS_T *)param)->r_gain.num,((MMAL_PARAMETER_AWB_GAINS_T *)param)->r_gain.den,((MMAL_PARAMETER_AWB_GAINS_T *)param)->b_gain.num,((MMAL_PARAMETER_AWB_GAINS_T *)param)->b_gain.den);
       break;
  case MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION:
       printf("+           src=%d\n",((MMAL_PARAMETER_DRC_T  *)param)->strength );
       break;
  case MMAL_PARAMETER_EXPOSURE_COMP:
       printf("+           exposure_comp=%d\n",((MMAL_PARAMETER_INT32_T *)param)->value);
       break;
  case MMAL_PARAMETER_EXPOSURE_MODE:
       printf("+           exaposure_mode=%d\n",((MMAL_PARAMETER_EXPOSUREMODE_T  *)param)->value);
       break;
  case MMAL_PARAMETER_ISO:
       printf("+           iso=%d\n",((MMAL_PARAMETER_UINT32_T  *)param)->value);
       break;
  case MMAL_PARAMETER_ROTATION:
       printf("+           rotation=%d\n",((MMAL_PARAMETER_INT32_T  *)param)->value);
       break;
  case MMAL_PARAMETER_SHUTTER_SPEED:
       printf("+           shutterspeed=%u\n",((MMAL_PARAMETER_UINT32_T *)param)->value);
       break;
  case MMAL_PARAMETER_VIDEO_STABILISATION:
       printf("+           video_stabilisation=%d\n",((MMAL_PARAMETER_BOOLEAN_T *)param)->enable);
       break;
  case MMAL_PARAMETER_ANALOG_GAIN:
       printf("+           analog_gain=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_ANNOTATE:
       printf("+           annotate=stuff\n");
       break;
  case MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG:
       printf("+           custom_sensor_config=%d\n",((MMAL_PARAMETER_UINT32_T *)param)->value);
       break;
  case MMAL_PARAMETER_CAMERA_NUM:
       printf("+           video_stabilisation=%d\n",((MMAL_PARAMETER_UINT32_T *)param)->value);
       break;
  case MMAL_PARAMETER_CAPTURE_STATS_PASS:
       printf("+           capture_stats_pass=%d\n",((MMAL_PARAMETER_BOOLEAN_T *)param)->enable);
       break;
  case MMAL_PARAMETER_COLOUR_EFFECT:
       printf("+           colour_effect=%d %d %d\n",((MMAL_PARAMETER_COLOURFX_T *)param)->enable,((MMAL_PARAMETER_COLOURFX_T *)param)->u,((MMAL_PARAMETER_COLOURFX_T *)param)->v);
       break;
  case MMAL_PARAMETER_CONTRAST:
       printf("+           contrast=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_DIGITAL_GAIN:
       printf("+           digital_gain=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_EXP_METERING_MODE:
       printf("+           exp_metering_mode=%d\n",((MMAL_PARAMETER_EXPOSUREMETERINGMODE_T  *)param)->value);
       break;
  case MMAL_PARAMETER_FLICKER_AVOID:
       printf("+           flicker_avoid=%d\n",((MMAL_PARAMETER_FLICKERAVOID_T  *)param)->value);
       break;
  case MMAL_PARAMETER_IMAGE_EFFECT:
       printf("+           image_effect=%d\n",((MMAL_PARAMETER_IMAGEFX_T  *)param)->value);
       break;
  case MMAL_PARAMETER_INPUT_CROP:
       printf("+           input_crop=%d,%d %d,%d\n",((MMAL_PARAMETER_INPUT_CROP_T *)param)->rect.x,((MMAL_PARAMETER_INPUT_CROP_T *)param)->rect.y,((MMAL_PARAMETER_INPUT_CROP_T *)param)->rect.width,((MMAL_PARAMETER_INPUT_CROP_T *)param)->rect.height);
       break;
  case MMAL_PARAMETER_MIRROR:
       printf("+           mirror=%d\n",((MMAL_PARAMETER_MIRROR_T  *)param)->value);
       break;
  case MMAL_PARAMETER_SATURATION:
       printf("+           saturation=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_SHARPNESS:
       printf("+           sharpness=%d/%d\n",((MMAL_PARAMETER_RATIONAL_T  *)param)->value.num,((MMAL_PARAMETER_RATIONAL_T  *)param)->value.den);
       break;
  case MMAL_PARAMETER_STEREOSCOPIC_MODE:
       printf("+           steroscopic_mode=%d %d %d\n",((MMAL_PARAMETER_STEREOSCOPIC_MODE_T  *)param)->mode,((MMAL_PARAMETER_STEREOSCOPIC_MODE_T  *)param)->decimate,((MMAL_PARAMETER_STEREOSCOPIC_MODE_T  *)param)->swap_eyes);
       break;

  default: 
       printf("+           fixme=%s\n",idtos(param->id));
 }

}


MMAL_STATUS_T mmal_component_create(const char *name,MMAL_COMPONENT_T **component)
{
 int a;
 char *p;
 MMAL_STATUS_T (*orig)(const char *name,MMAL_COMPONENT_T **component);
 orig=dlsym(RTLD_NEXT, "mmal_component_create");
 MMAL_STATUS_T rc=(*orig)(name,component);
 printf("++++++++ mmal_component_create(%s,?) =%d ?=%p\n",name,rc,*component);
 printf("+           priv=%p\n",(*component)->priv);
 printf("+           userdata=%p\n",(*component)->userdata);
 printf("+           name=\"%s\"\n",(*component)->name);
 printf("+           is_enabled=%d\n",(*component)->is_enabled);
 printf("+           control=%p\n",(*component)->control);
 printf("+           input_num=%d\n",(*component)->input_num);
 for (a=0;a<(*component)->input_num;a++)
  printf("+           input[%d]=%p\n",a,(*component)->input[a]);
 printf("+           output_num=%d\n",(*component)->output_num);
 for (a=0;a<(*component)->output_num;a++)
  printf("+           output[%d]=%p\n",a,(*component)->output[a]);
 printf("+           clock_num=%d\n",(*component)->clock_num);
 for (a=0;a<(*component)->clock_num;a++)
  printf("+           clock[%d]=%p\n",a,(*component)->clock[a]);
 printf("+           port_num=%d\n",(*component)->port_num);
 for (a=0;a<(*component)->port_num;a++)
  printf("+           port[%d]=%p\n",a,(*component)->port[a]);
 printf("+           id=%d\n",(*component)->id);

 p=malloc(1000);
 sprintf(p,"%s@%p-control",(*component)->name,*component);
 addname(p,(*component)->control);
 for (a=0;a<(*component)->input_num;a++)
 {
  sprintf(p,"%s@%p-input%d",(*component)->name,*component,a); 
  addname(p,(*component)->input[a]);
 }
 for (a=0;a<(*component)->output_num;a++)
 {
  sprintf(p,"%s@%p-output%d",(*component)->name,*component,a); 
  addname(p,(*component)->output[a]);
 }

 return rc;
}

MMAL_STATUS_T mmal_port_parameter_set_int32(MMAL_PORT_T *port, uint32_t id, int32_t value)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,uint32_t id, int32_t value);
 orig=dlsym(RTLD_NEXT, "mmal_port_parameter_set_int32");
 MMAL_STATUS_T rc=(*orig)(port,id,value);
 /*printf("++++++++ mmal_port_parameter_set_int32(%p,%x,%d) = %d\n",port,id,value,rc);*/
 printf("++++++++ mmal_port_parameter_set_int32(%s,%x,%d) = %d\n",getname(port),id,value,rc);
 decode_param(id);
 return rc;
}

MMAL_STATUS_T mmal_port_parameter_set_uint32(MMAL_PORT_T *port, uint32_t id, uint32_t value)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,uint32_t id, uint32_t value);
 orig=dlsym(RTLD_NEXT, "mmal_port_parameter_set_uint32");
 MMAL_STATUS_T rc=(*orig)(port,id,value);
 /*printf("++++++++ mmal_port_parameter_set_uint32(%p,%x,%d) = %d\n",port,id,value,rc);*/
 printf("++++++++ mmal_port_parameter_set_uint32(%s,%x,%d) = %d\n",getname(port),id,value,rc);
 decode_param(id);
 return rc;
}

MMAL_STATUS_T mmal_port_enable(MMAL_PORT_T *port, MMAL_PORT_BH_CB_T cb)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,MMAL_PORT_BH_CB_T cb);
 orig=dlsym(RTLD_NEXT, "mmal_port_enable");
 MMAL_STATUS_T rc=(*orig)(port,cb);
 /*printf("++++++++ mmal_port_enable(%p,%p) = %d\n",port,cb,rc);*/
 printf("++++++++ mmal_port_enable(%s,%p) = %d\n",getname(port),cb,rc);
 return rc;
}

MMAL_STATUS_T mmal_port_format_commit(MMAL_PORT_T *port)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port);
 orig=dlsym(RTLD_NEXT, "mmal_port_format_commit");
 MMAL_STATUS_T rc=(*orig)(port);
 /*printf("++++++++ mmal_port_format_commit(%p) = %d\n",port,rc);*/
 printf("++++++++ mmal_port_format_commit(%s) = %d\n",getname(port),rc);
 return rc;
}

MMAL_STATUS_T mmal_component_disable(MMAL_COMPONENT_T *component)
{
 MMAL_STATUS_T (*orig)(MMAL_COMPONENT_T *component);
 orig=dlsym(RTLD_NEXT, "mmal_component_disable");
 MMAL_STATUS_T rc=(*orig)(component);
 printf("++++++++ mmal_component_disable(%p) = %d\n",component,rc);
 return rc;
}

MMAL_STATUS_T mmal_port_disable(MMAL_PORT_T *port)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port);
 orig=dlsym(RTLD_NEXT, "mmal_port_disable");
 MMAL_STATUS_T rc=(*orig)(port);
 /*printf("++++++++ mmal_port_disable(%p) = %d\n",port,rc);*/
 printf("++++++++ mmal_port_disable(%s) = %d\n",getname(port),rc);
 return rc;
}

MMAL_STATUS_T mmal_port_parameter_set_boolean(MMAL_PORT_T *port, uint32_t id, MMAL_BOOL_T value)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,uint32_t id, MMAL_BOOL_T value);
 orig=dlsym(RTLD_NEXT, "mmal_port_parameter_set_boolean");
 MMAL_STATUS_T rc=(*orig)(port,id,value);
 /*printf("++++++++ mmal_port_parameter_set_boolean(%p,%x,%d) = %d\n",port,id,value,rc);*/
 printf("++++++++ mmal_port_parameter_set_boolean(%s,%x,%d) = %d\n",getname(port),id,value,rc);
 decode_param(id);
 return rc;
}

MMAL_STATUS_T mmal_port_send_buffer(MMAL_PORT_T *port,MMAL_BUFFER_HEADER_T *buffer)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,MMAL_BUFFER_HEADER_T *buffer);
 orig=dlsym(RTLD_NEXT, "mmal_port_send_buffer");
 MMAL_STATUS_T rc=(*orig)(port,buffer);
 printf("++++++++ mmal_port_send_buffer(%s,%p) = %d\n",getname(port),buffer,rc);
 return rc;
}

unsigned int mmal_queue_length(MMAL_QUEUE_T *queue)
{
 unsigned int (*orig)(MMAL_QUEUE_T *queue);
 orig=dlsym(RTLD_NEXT, "mmal_queue_length");
 unsigned int rc=(*orig)(queue);
 printf("++++++++ mmal_queue_length(%p) = %d\n",queue,rc);
 return rc;
}

MMAL_STATUS_T mmal_port_parameter_set_rational(MMAL_PORT_T *port, uint32_t id, MMAL_RATIONAL_T value)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,uint32_t id, MMAL_RATIONAL_T value);
 orig=dlsym(RTLD_NEXT, "mmal_port_parameter_set_rational");
 MMAL_STATUS_T rc=(*orig)(port,id,value);
 /*printf("++++++++ mmal_port_parameter_set_rational(%p,%x,%d/%d) = %d\n",port,id,value.num,value.den,rc);*/
 printf("++++++++ mmal_port_parameter_set_rational(%s,%x,%d/%d) = %d\n",getname(port),id,value.num,value.den,rc);
 decode_param(id);
 return rc;
}

MMAL_POOL_T *mmal_port_pool_create(MMAL_PORT_T *port,unsigned int headers, uint32_t payload_size)
{
 MMAL_POOL_T * (*orig)(MMAL_PORT_T *port,unsigned int headers, uint32_t payload_size);
 orig=dlsym(RTLD_NEXT, "mmal_port_pool_create");
 MMAL_POOL_T * rc=(*orig)(port,headers,payload_size);
 /*printf("++++++++ mmal_port_pool_create(%p,%d,%d) = %p\n",port,headers,payload_size,rc);*/
 printf("++++++++ mmal_port_pool_create(%s,%d,%d) = %p\n",getname(port),headers,payload_size,rc);
 return rc;
}

void mmal_port_pool_destroy(MMAL_PORT_T *port, MMAL_POOL_T *pool)
{
 void (*orig)(MMAL_PORT_T *port,MMAL_POOL_T *pool);
 orig=dlsym(RTLD_NEXT, "mmal_port_pool_destroy");
 (*orig)(port,pool);
 /*printf("++++++++ mmal_port_pool_destroy(%p,%p)\n",port,pool);*/
 printf("++++++++ mmal_port_pool_destroy(%s,%p)\n",getname(port),pool);
}

MMAL_STATUS_T mmal_component_destroy(MMAL_COMPONENT_T *component)
{
 MMAL_STATUS_T (*orig)(MMAL_COMPONENT_T *component);
 orig=dlsym(RTLD_NEXT, "mmal_component_destroy");
 MMAL_STATUS_T rc=(*orig)(component);
 printf("++++++++ mmal_component_destroy(%p) = %d\n",component,rc);
 return rc;
}

MMAL_BUFFER_HEADER_T *mmal_queue_get(MMAL_QUEUE_T *queue)
{
 MMAL_BUFFER_HEADER_T * (*orig)(MMAL_QUEUE_T *queue);
 orig=dlsym(RTLD_NEXT, "mmal_queue_get");
 MMAL_BUFFER_HEADER_T * rc=(*orig)(queue);
 printf("++++++++ mmal_queue_get(%p) = %p\n",queue,rc);
 return rc;
}

MMAL_STATUS_T mmal_port_parameter_set(MMAL_PORT_T *port,   const MMAL_PARAMETER_HEADER_T *param)
{
 MMAL_STATUS_T (*orig)(MMAL_PORT_T *port,const MMAL_PARAMETER_HEADER_T *param);
 orig=dlsym(RTLD_NEXT, "mmal_port_parameter_set");
 MMAL_STATUS_T rc=(*orig)(port,param);
 /*printf("++++++++ mmal_port_parameter_set(%p,(%x,%d)) = %d\n",port,param->id,param->size,rc);*/
 printf("++++++++ mmal_port_parameter_set(%s,(%x,%d)) = %d\n",getname(port),param->id,param->size,rc);
 decode_param(param->id);
 decode_param_pack(param);
 return rc;
}

MMAL_STATUS_T mmal_component_enable(MMAL_COMPONENT_T *component)
{
 MMAL_STATUS_T (*orig)(MMAL_COMPONENT_T *component);
 orig=dlsym(RTLD_NEXT, "mmal_component_enable");
 MMAL_STATUS_T rc=(*orig)(component);
 printf("++++++++ mmal_component_enable(%p) = %d\n",component,rc);
 return rc;
}


/*mmal_buffer_header_mem_lock*/
/*mmal_buffer_header_mem_unlock*/
/*mmal_buffer_header_release*/
/*mmal_connection_create
mmal_connection_destroy
mmal_connection_enable
mmal_log_category
mmal_port_parameter_get
mmal_status_to_int
mmal_util_rgb_order_fixed*/

