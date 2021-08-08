# name=Xctrl

# imports
import mixer
import time
import midi
import transport
import ui
import device
import array
import playlist
import general
import arrangement

# const
alive = [0xf0,0x00,0x00,0x66,0x14,0x00,0xf7]
ok = [0xF0,0x00,0x20,0x32,0x58,0x54,0x00,0xF7]
ak = [0xF0,0x00,0x00,0x66,0x58,0x01,0x30,0x31,0x35,0x36,0x34,0x30,0x37,0x33,0x39,0x37,0x36,0xF7]
first_fader_code = 0xe0
select_button_code = 0x18
mute_button_code = 0x10
arm_buton_code = 0x00
solo_button_code = 0x08
first_screen = 0x20
first_channel_pan = 0x10
first_left_pan_led = 0x30
first_right_pan_led = 0x38
first_enc_button_code = 0x20
first_function_button = 0x36
digit_numbers = [0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f]
fader_number = 8



# status
get_resp = False
is_sync = False
page = 1
is_moving = False
select_led_is_out = False
actual_selected_track = 0
last_alive = 0
is_closing = False
time_from_ak = 0
connected = False

# status memory
channel_pan = 9*[-10]
channel_mute = 9*[-1]
channel_arm = 9*[-1]
channel_volume = 9*[-10]
channel_solo = 9*[-10]
master_value = -10
old_millis = 2*[-1]
old_seconds = 2*[-1]
old_minutes = 3*[-1]
init = 0x00
save_led_status = -1
screen_names = 9*[""]
screen_color = 9*[-10]
page_old = -1
smtpe_mode = -1
undo_index = -1
function_led_status = 4*[-1]
scrub_status = 0



def OnDeInit():
    global is_sync
    global is_closing
    global connected
    is_sync = False
    is_closing = True
    connected = False
    print("is_closing")

def OnInit():
    global last_alive
    global is_closing
    is_closing = False
    last_alive = round(time.time() * 1000)
    print("init... waiting 5 sec...")
    device.setHasMeters()

def OnUpdateMeters():
    for i in range(page,page+ fader_number):
        v = mixer.getTrackPeaks(i,2)
        # a modifier !
        offset = (i - page) * 16
        device.midiOutMsg(0xd0 + (int(mp(v,0,1,offset,(offset + 8))) << 8) + (0x00<< 16))


def select(i):
    global page
    global select_button_code
    global actual_selected_track
    global select_led_is_out
    selected_track = (mixer.trackNumber() -page) + select_button_code
    if selected_track != actual_selected_track:
        if select_led_is_out == False:
            for u in range(page,(page+fader_number)):
                if ((u -page) + select_button_code) != selected_track:
                    device.midiOutMsg(0x90 + ((u-page) + select_button_code << 8) + (0x00<< 16))
                    ##print("refershing select")
        actual_selected_track = selected_track
        if mixer.trackNumber() >= page and mixer.trackNumber()  <= page + (fader_number-1):
            device.midiOutMsg(0x90 + (selected_track << 8) + (0x02<< 16))
            ##print("refershing select")
            select_led_is_out = False
        else:
            select_led_is_out = True
            

def faders(i):
    
    global page
    global is_moving

    if is_moving == False:  
        if channel_volume[i-page] != mixer.getTrackVolume(i):
            ##print("refershing faders")
            device.midiOutMsg(((first_fader_code+i)-page) + (int(mp((mixer.getTrackVolume(i)/2),0.0,1.0,0,124))<< 8)+ (int(mp((mixer.getTrackVolume(i)),0.0,1.0,0,127)) << 16))
            #print("fader changed : (ch" + str(i) + ") " + str(mixer.getTrackVolume(i))+ " > " + str(channel_volume[i-page]))
            channel_volume[i-page] = mixer.getTrackVolume(i)
        #else:
            #print("fader NOT changed : (ch" + str(i) + ") " + str(mixer.getTrackVolume(i))+ " > " + str(channel_volume[i]))
                
                
def master():
    global is_moving
    global master_value
    if is_moving == False:    
        if master_value != mixer.getTrackVolume(0):
            device.midiOutMsg(0xe8 + (int(mp((mixer.getTrackVolume(0)/2),0.0,1.0,0,124))<< 8)+ (int(mp((mixer.getTrackVolume(0)),0.0,1.0,0,127)) << 16))
            print("fader changed : (ch" + str(0) + ") " + str(mixer.getTrackVolume(0))+ " > " + str(master_value))
            master_value = mixer.getTrackVolume(0)

def pan(i):
    global page
    global is_moving
    global channel_pan
    left_led_code = [0x7f,0x7e,0x7c,0x78,0x70,0x60]
    right_led_code = [0x01,0x03,0x07,0x0f,0x1f,0x3f]
    if is_moving == False:
        actual_pan = mixer.getTrackPan(i)
        #print(actual_pan)
        if channel_pan[i-page] != actual_pan:
            ##print("refershing pan")
            #print("PAN changed : (ch" + str(i) + ") " + str(actual_pan) +" > " + str(channel_pan[i-page]) )
            if actual_pan < 0.02 and actual_pan > -0.02:
                device.midiOutMsg(0xb0 + (((first_left_pan_led + i)-page)<< 8) + (0x41 << 16))           #pan is center
                device.midiOutMsg(0xb0 + (((first_right_pan_led + i)-page)<< 8) + (0x60 << 16))
           
            if actual_pan < -0.05:
                if actual_pan < -0.05:
                    device.midiOutMsg(0xb0 + (((first_right_pan_led + i)-page)<< 8) + (0x00 << 16))
                    device.midiOutMsg(0xb0 + (((first_left_pan_led + i)-page)<< 8) + (0x40 << 16))
                p = int(mp(actual_pan,-1,-0.02,1,60))
                p = int(p/10.5) # 63 / 6 = 10.5
                device.midiOutMsg(0xb0 + (((first_left_pan_led + i)-page)<< 8) + (left_led_code[p]<< 16))
           
            if actual_pan > 0.05:
                if actual_pan > 0.02:
                    device.midiOutMsg(0xb0 + (((first_left_pan_led + i)-page)<< 8) + (0x40 << 16))
                p = int(mp(actual_pan,0.02,1.0,1,60))
                p = int(p/10.5) # 63 / 6 = 10.5
                device.midiOutMsg(0xb0 + (((first_right_pan_led + i)-page)<< 8) + (right_led_code[p]<< 16))
            channel_pan[i-page] = actual_pan
        #else:
            #print("PAN NOT changed : (ch" + str(i) + ") " + str(actual_pan) +" > " + str(channel_pan[i]) )
                
def force_refresh():
    global channel_mute
    global channel_pan
    global channel_volume
    global screen_color
    global screen_names
    global undo_index
    global old_millis
    global old_minutes
    global old_seconds
    global page_old
    global channel_arm
    global channel_solo
    global master_value
    global scrub_status
    global save_led_status
    global function_led_status
    global smtpe_mode
    smtpe_mode = -1
    scrub_status = 0
    save_led_status = -1
    old_seconds = -10
    old_millis = -10
    old_minutes = -10
    page_old = -10
    undo_index = -1
    master_value = -10
    function_led_status = 4*[-1]
    for i in range(0,fader_number):
        channel_solo[i] = -10
        channel_arm[i] = -10
        channel_pan[i] = -10
        channel_volume[i] = -10
        channel_mute[i] = -1
        screen_color[i] = -10
        screen_names[i] = ""
        
        
def mute(i):
    global page
    global mute_button_code
    global channel_mute
    if channel_mute[i-page] != mixer.isTrackMuted(i):
        if mixer.isTrackMuted(i) == True:
            device.midiOutMsg(0x90 + ((i-page) + mute_button_code << 8) + (0x06<< 16))
            ##print("refershing mute")
        else:
            device.midiOutMsg(0x90 + ((i-page) + mute_button_code << 8) + (0x00<< 16))
            #print("refershing mute")
        channel_mute[i-page] = mixer.isTrackMuted(i)
            
def arm(i):
    global page
    global arm_buton_code
    global channel_arm
    ##print("refershing arm")
    if channel_arm[i-page] != mixer.isTrackArmed(i):
        if mixer.isTrackArmed(i) == True:
            device.midiOutMsg(0x90 + ((i-page) + arm_buton_code << 8) + (0x06<< 16))
        else:
            device.midiOutMsg(0x90 + ((i-page) + arm_buton_code << 8) + (0x00<< 16))
        channel_arm[i-page] = mixer.isTrackArmed(i)
            
def solo(i):
    global page
    global solo_button_code
    global channel_solo
    if channel_solo[i -page]!= mixer.isTrackSolo(i):
            ##print("refershing solo")
        if mixer.isTrackSolo(i) == True:
            device.midiOutMsg(0x90 + ((i-page) + solo_button_code << 8) + (0x06<< 16))
        else:
            device.midiOutMsg(0x90 + ((i-page) + solo_button_code << 8) + (0x00<< 16))
        channel_solo[i-page] = mixer.isTrackSolo(i)  
                

def screens(i):
    global page
    global is_moving
    global screen_names
    global screen_color

    if is_moving == False:
        
        if (screen_names[i-page] != mixer.getTrackName(i)) or (screen_color[i -page] != mixer.getTrackColor(i)):
            print("refershing screens")
            screen_names[(i-page)] = mixer.getTrackName(i)
            screen_color[(i -page)] = mixer.getTrackColor(i)
            print(str(screen_names[i-page]) + " > " + mixer.getTrackName(i))
            print(str(screen_color[i -page]) + " > " + str(mixer.getTrackColor(i)))

            header = [0xf0,0x00,0x00,0x66,0x58]
            channel = ((i - page)) + first_screen
            cc = define_color(mixer.getTrackColor(i))
            txt1 = "CH"        
            ch = str(i)
            txt1 = txt1 + ch        
            while len(txt1) <7 :
                txt1 = txt1 + " "
            txt1 = bytes(txt1,"ascii") 
            txt2 = mixer.getTrackName(i)
            if len(txt2) > 7:
                txt2 = txt2.replace(' ', '') 
                for i in range(1,len(txt2),1):
                    if len(txt2) > 7:
                        txt2 = txt2[:i] + txt2[i+1:]      
            while len(txt2) < 7 :
                txt2 = txt2 + " "
            txt2 =  bytes(txt2,"ascii")
            ender = 0xf7
            total = []
            for u in range(0,len(header)):
                total.append(header[u])
            total.append(channel)
            total.append(cc)
            for y in range(0,len(txt1)):
                total.append(txt1[y])
            for t in range(0,len(txt2)):
                total.append(txt2[t])
            total.append(ender)
            device.midiOutSysex(bytes(total))
    

def Int2RGBA(Int):
    blue = Int & 255
    green = (Int >> 8) & 255
    red = (Int >> 16) & 255
    alpha = (Int >> 24) & 255
    return(RGB_2_HSV((red,green,blue)))
    
def define_color(clr):
    c_hsv = Int2RGBA(clr)
    
    if c_hsv[0] < 0:
        c_hsv = (c_hsv[0] * -1,c_hsv[1],c_hsv[2])
    

    if c_hsv[2] > 30 and c_hsv[1] > 40:
    
        if (c_hsv[0] >= 0 and c_hsv[0] < 28) or (c_hsv[0] > 242 and c_hsv[0] <= 255): # rouge
            return 0x01
            
        if (c_hsv[0] > 28 and c_hsv[0] < 53): #jaune
            return 0x03
        
        if (c_hsv[0] > 50 and c_hsv[0] < 117): #vert
            return 0x02
        
        if (c_hsv[0] > 118 and c_hsv[0] < 140): #cyan
            return 0x06
            
        if (c_hsv[0] > 141 and c_hsv[0] < 190): #bleu
            return 0x04
        
        if (c_hsv[0] > 191 and c_hsv[0] < 241): #rose
            return 0x05
            
            
            
    if c_hsv[2] < 30:
        return 0x00
    if c_hsv[2] > 138 or c_hsv[1] < 40:
        return 0x07
    return 0x07
        
    
def RGB_2_HSV(RGB):
    ''' Converts an integer RGB tuple (value range from 0 to 255) to an HSV tuple '''
    # Unpack the tuple for readability
    R, G, B = RGB
    # Compute the H value by finding the maximum of the RGB values
    RGB_Max = max(RGB)
    RGB_Min = min(RGB)
    # Compute the value
    V = RGB_Max
    if V == 0:
        H = S = 0
        return (H,S,V)
    # Compute the saturation value
    S = 255 * (RGB_Max - RGB_Min) // V
    if S == 0:
        H = 0
        return (H, S, V)
    # Compute the Hue
    if RGB_Max == R:
        H = 0 + 43*(G - B)//(RGB_Max - RGB_Min)
    elif RGB_Max == G:
        H = 85 + 43*(B - R)//(RGB_Max - RGB_Min)
    else: # RGB_MAX == B
        H = 171 + 43*(R - G)//(RGB_Max - RGB_Min)
    return (H, S, V)

def save_led():
    global save_led_status
    if save_led_status != general.getChangedFlag():
        if general.getChangedFlag() > 0:
            device.midiOutMsg(0x90 + (0x50 << 8) + (0x02<< 16))
        else:
            device.midiOutMsg(0x90 + (0x50 << 8) + (0x00<< 16))
        save_led_status = general.getChangedFlag()

def undo_led():
    global  undo_index
    ind = general.getUndoLevelHint()
    ind_s = ind.split("/")
    if undo_index != (int(ind_s[0]) + int(ind_s[1])):
        if int(ind_s[0]) != int(ind_s[1]) :
            device.midiOutMsg(0x90 + (0x51 << 8) + (0x02<< 16))
        else:
            device.midiOutMsg(0x90 + (0x51 << 8) + (0x00<< 16))
        undo_index = int(ind_s[0]) + int(ind_s[1])

def save():
    save_led()
    transport.globalTransport(midi.FPT_Save,1)

def manage_window(index):
    if ui.getVisible(index) == 1:
        ui.setFocused(index)
        ui.escape()
        return
    else:
        ui.showWindow(index)
    
def OnMidiMsg(event):
    global is_sync
    global page
    global scrub_status
    
    if is_sync == True and device.isAssigned() == 1 :
        digits_display()
        send_alive()
        
        event.handled = False

        if event.status == 0x90 and event.data1 == 0x64: # zoom
            if event.data2 > 0x01:
                transport.globalTransport(midi.FPT_HZoomJog,1)
                device.midiOutMsg(0x90 + (0x64 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x64 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x53: # enter
            if event.data2 > 0x01:
                ui.enter()
                device.midiOutMsg(0x90 + (0x53 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x53 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x52: #cancel
            if event.data2 > 0x01:
                ui.escape()
                device.midiOutMsg(0x90 + (0x52 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x52 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x63: # up right
            if event.data2 > 0x01:
                ui.right()
                device.midiOutMsg(0x90 + (0x63 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x63 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x62: # up left
            if event.data2 > 0x01:
                ui.left()
                device.midiOutMsg(0x90 + (0x62 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x62 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x61: # up down
            if event.data2 > 0x01:
                ui.down()
                device.midiOutMsg(0x90 + (0x61 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x61 << 8) + (0x00<< 16))
            event.handled = True


        if event.status == 0x90 and event.data1 == 0x60: # up key
            if event.data2 > 0x01:
                ui.up()
                device.midiOutMsg(0x90 + (0x60 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x60 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x47: # menu
            if event.data2 > 0x01:
                #transport.globalTransport(midi.FPT_Menu,1)
                ui.horZoom(1)
                device.midiOutMsg(0x90 + (0x47 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x47 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x65 and event.data2 > 1: #scrub
            if scrub_status == 0:
                device.midiOutMsg(0x90 + (0x65 << 8) + (0x02<< 16))
                scrub_status =1
            else:
                device.midiOutMsg(0x90 + (0x65 << 8) + (0x00<< 16))
                scrub_status =0
            event.handled = True

        if event.status == 0xB0 and event.data1 == 0x3c: # jogle
            if event.data2 < 30:
                if scrub_status == 0:
                    transport.setSongPos(transport.getSongPos(0)+400,0)
                else:
                    transport.setSongPos(transport.getSongPos(0)+50,0)
            if event.data2 > 30:
            
                if scrub_status == 0:
                    transport.setSongPos(transport.getSongPos(0)-400,0)
                else:
                    transport.setSongPos(transport.getSongPos(0)-50,0)
            event.handled = True  

        if event.status == 0x90 and event.data1 == 0x56: #change mode (song / pattern)
            if event.data2 > 0x01:

                transport.setLoopMode()
                device.midiOutMsg(0x90 + (0x56 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x56 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x54: #set marker
            if event.data2 > 0x01:
                arrangement.addAutoTimeMarker(arrangement.currentTime(1),"Auto")
                device.midiOutMsg(0x90 + (0x54 << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x54 << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 >= 0x36 and event.data1 <= 0x3d and event.data2 > 0x01: # button function
            if event.data1 - first_function_button <= 3:
                manage_window(event.data1 - first_function_button)
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x35 and event.data2 > 0x01: # change time display     
            ui.setTimeDispMin()
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x51 and event.data2 > 0x01: #undo
            refresh(0)
            general.undoUp()
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x50 and event.data2 > 0x01: # save
            save()
            event.handled = True
        
        if event.status == 0x90 and event.data1 == 0x5e and event.data2 > 0x01: # play
            #transport.globalTransport(10,10,2,15)
            transport.start()
            #digits_display()
            if transport.isPlaying() == True:
                device.midiOutMsg(0x90 + (0x5e << 8) + (0x01<< 16))
                device.midiOutMsg(0x90 + (0x5D << 8) + (0x00<< 16))
            else:
                device.midiOutMsg(0x90 + (0x5e << 8) + (0x00<< 16))
                device.midiOutMsg(0x90 + (0x5D << 8) + (0x02<< 16))
            device.midiOutMsg(0x90 + (0x5D << 8) + (0x00<< 16))
            event.handled = True
            
        if event.status == 0x90 and event.data1 == 0x5D and event.data2 > 0x01: # stop
            transport.stop()
            device.midiOutMsg(0x90 + (0x5e << 8) + (0x00<< 16))
            device.midiOutMsg(0x90 + (0x5D << 8) + (0x02<< 16))
        # digits_display()
            event.handled = True
        
        if event.status == 0x90 and event.data1 == 0x5F and event.data2 > 0x01: # REC
            transport.record()
            if transport.isRecording() == True:
                device.midiOutMsg(0x90 + (0x5f << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x5f << 8) + (0x00<< 16))
            event.handled = True

        if event.status == 0x90 and event.data1 == 0x5B: # rewind
            transport.rewind(2,15)
            if event.data2 > 0x10:
                device.midiOutMsg(0x90 + (0x5b << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x5B << 8) + (0x00<< 16))
                transport.rewind(0,15)
            event.handled = True
                
        if event.status == 0x90 and event.data1 == 0x5c: # fastforward
            transport.fastForward(2,15)
            if event.data2 > 0x10:
                device.midiOutMsg(0x90 + (0x5c << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (0x5c << 8) + (0x00<< 16))
                transport.fastForward(0,15)
            event.handled = True
            
        if event.data2 >= 0:
            ##print(event.status)
            # status = 1er octet
    
            if event.status >= first_fader_code and event.status <= first_fader_code + (fader_number -1): # faders
                is_moving = True
                mixer.setTrackVolume((event.status - (first_fader_code -1)+ page -1),mp(event.data2,0,127,0.0,1.0))
                #faders() a modifier
                event.handled = True

            if event.status == 0xe8: # Master
                is_moving = True
                mixer.setTrackVolume(0,mp(event.data2,0,127,0.0,1.0))
                #faders()
                event.handled = True

            if event.status == 0xb0 and event.data1 >= first_channel_pan and event.data1 <= first_channel_pan + (fader_number -1): # pan
                #is_moving = True
                
                actual_pan = mixer.getTrackPan((event.data1 - first_channel_pan) + (page))
                if event.data2 > 0x40:
                    mixer.setTrackPan((event.data1 - first_channel_pan) + (page),actual_pan - 0.03) 
                else:
                    mixer.setTrackPan((event.data1 - first_channel_pan) + (page),actual_pan + 0.03)
                #mixer.setChannelPan((event.status - (first_fader_code -1)+ page -1),mp(event.data2,0,127,0.0,1.0))
                refresh(7)#pan()
                event.handled = True
                
            if event.status == 0x90 and (event.data1 >= 0x18 and event.data1 <= 0x1f): # Select
                mixer.setTrackNumber((event.data1 + page) - select_button_code)
                refresh(1)#select()
                event.handled = True
                
            if event.status == 0x90 and (event.data1 >= 0x20 and event.data1 <= 0x27) and event.data2 > 0: # reset pan (encoders button)
                mixer.setTrackPan((event.data1 - first_enc_button_code)+page,0)
                ##print((event.data1 - mute_button_code)+page)
                event.handled = True
            
            if event.status == 0x90 and (event.data1 >= 0x10 and event.data1 <= 0x17) and event.data2 > 0: # mute
                mixer.muteTrack((event.data1 - mute_button_code)+page)
                ##print((event.data1 - mute_button_code)+page)
                refresh(3)#mute()
                event.handled = True
                
            if event.status == 0x90 and (event.data1 >= 0x00 and event.data1 <= 0x07) and event.data2 > 0: # arm
                mixer.armTrack((event.data1 - arm_buton_code)+page)
                ##print((event.data1 - mute_button_code)+page)
                refresh(4)#arm()
                event.handled = True
            
            if event.status == 0x90 and (event.data1 >= 0x08 and event.data1 <= 0x0f) and event.data2 > 0: # solo
                mixer.soloTrack((event.data1 - solo_button_code)+page)
                refresh(5)#solo()
                event.handled = True
                
            if event.status == 0x90 and (event.data1 >= 0x68 and event.data1 <= 0x70): # is moving
                if event.data2 == 0x7f :
                    is_moving = True
                else:
                    is_moving = False
                event.handled = True
                
            if event.status == 0x90 and event.data1 == 0x2e: # ##print("refershingk -                     
                if event.data2 == 0x7f:
                    if page - fader_number > 0 :
                        page = page - fader_number
                        mixer.setTrackNumber(page)
                    else:
                        page = 113
                        mixer.setTrackNumber(page)
                    device.midiOutMsg(0x90 + (0x2e << 8) + (0x02<< 16))
                    #screens()
                    force_refresh()
                    refresh(0)
                else:
                    device.midiOutMsg(0x90 + (0x2e << 8) + (0x00<< 16))
                    #screens()
                    force_refresh()
                    refresh(0)
                event.handled = True
                
                    
            if event.status == 0x90 and event.data1 == 0x2f: # ##print("refershingk +            
                if event.data2 == 0x7f:
                    if page + fader_number < 121 :
                        page = page + fader_number
                        mixer.setTrackNumber(page)
                    else:
                        page = 1
                        mixer.setTrackNumber(page)
                    device.midiOutMsg(0x90 + (0x2f << 8) + (0x02<< 16))
                    #screens()
                    force_refresh()
                    refresh(0)
                else:
                    device.midiOutMsg(0x90 + (0x2f << 8) + (0x00<< 16))
                    #screens()
                    force_refresh()
                    refresh(0)
                event.handled = True

            if event.status == 0x90 and event.data1 == 0x30: # fader -                     
                if event.data2 == 0x7f:
                    if page - 1 > 0 :
                        page = page - 1
                        mixer.setTrackNumber(page)
                    else:
                        page = 113
                        mixer.setTrackNumber(page)
                    device.midiOutMsg(0x90 + (0x30 << 8) + (0x02<< 16))
                    force_refresh()
                    refresh(0)               
                else:
                    device.midiOutMsg(0x90 + (0x30 << 8) + (0x00<< 16))
                    force_refresh()
                    refresh(0)
                event.handled = True 
                    
            if event.status == 0x90 and event.data1 == 0x31: # fader +            
                if event.data2 == 0x7f:
                    if page + 1 < 113 :
                        page = page + 1
                        mixer.setTrackNumber(page)
                    else:
                        page = 1
                        mixer.setTrackNumber(page)
                    device.midiOutMsg(0x90 + (0x31 << 8) + (0x02<< 16))
                    force_refresh()
                    refresh(0)
                else:
                    device.midiOutMsg(0x90 + (0x31 << 8) + (0x00<< 16))
                    force_refresh()
                    refresh(0)
                event.handled = True
        event.handled = True


def OnSysEx(event):

    global ok
    global ak
    global is_sync
    global is_closing
    global get_resp
    global time_from_ak
    global connected
    if is_closing == False and device.isAssigned() == 1:
        #if event.sysex:
        event.handled = False
        u = event.sysex
        
        #print(u)
        #device.midiOutSysex(bytes(alive))
        
        if comp_msg(u,ok) == True: 
            if get_resp == False and is_closing == False:
                get_resp = True
                print("responce : OK!")
                event.handled = True

        if get_resp == True:
            if comp_msg(u,ak) == True:
                if is_closing == False:
                    if connected == False:
                        is_sync = True
                        print("sync : OK!")
                        connected = True
                    time_from_ak = round(time.time() * 1000)
                    event.handled = True
        
                

    event.handled = True
                
def send_alive():
    global alive
    global is_sync
    global last_alive
    global init

    if device.isAssigned() == 1 and is_sync == True:
        ms = round(time.time() * 1000)
        if ms - last_alive > 6000:
            try:
                device.midiOutSysex(bytes(alive))
            except:
                print("error on sending")
            last_alive = ms
            if is_sync == True and device.isAssigned() == 1:
                if init == 0:
                    force_refresh()
                    refresh(0)
                    init = 1
                    print("init... OK!")
                    
            print("send_alive")
        # print(time.process_time())
        # print(time.process_time() - last_alive)

def comp_msg(array1,array2):
    if len(array1) == len(array2):
        for i in range(len(array1)):
            if array1[i] != array2[i]:
                ##print("ok")
            #else:
                 #print("nop")
                 return False
    return True
    
    
def mp(value,old_min,old_max,new_min,new_max):
    r = (((value - old_min) * (new_max-new_min)) / (old_max-old_min))+new_min
    return r

def num_to_digits(num):
    number = num
    numList = [int(digit) for digit in str(number)]
    return numList
    
def digits_display():
    
    global digit_numbers
    global old_millis
    global old_minutes
    global old_seconds
    global page
    global page_old
    global smtpe_mode

    if smtpe_mode != ui.getTimeDispMin():
        smtpe_mode = ui.getTimeDispMin()
        if ui.getTimeDispMin() == 0:
            device.midiOutMsg(0x90 + (0x72 << 8) + (0x02<< 16))
            device.midiOutMsg(0x90 + (0x71 << 8) + (0x00<< 16))
        else:
            device.midiOutMsg(0x90 + (0x71 << 8) + (0x02<< 16))
            device.midiOutMsg(0x90 + (0x72 << 8) + (0x00<< 16))

    millis = num_to_digits(playlist.getVisTimeTick()) #miliseconds
    if millis != old_millis:
        if len(millis) > 1:
            device.midiOutMsg(0xB0 + (0x6B << 8) + (digit_numbers[millis[1]]<< 16))
            device.midiOutMsg(0xB0 + (0x6a << 8) + (digit_numbers[millis[0]]<< 16))
            device.midiOutMsg(0xB0 + (0x69 << 8) + (digit_numbers[0]<< 16))
        else:
            device.midiOutMsg(0xB0 + (0x6B << 8) + (digit_numbers[millis[0]]<< 16))
            device.midiOutMsg(0xB0 + (0x6a << 8) + (digit_numbers[0]<< 16))
            device.midiOutMsg(0xB0 + (0x69 << 8) + (digit_numbers[0]<< 16))
        old_millis = millis

    minutes = num_to_digits(playlist.getVisTimeBar()) # minutes
    if minutes != old_minutes:
        if ui.getTimeDispMin() == 0:
            device.midiOutMsg(0xB0 + (0x66 << 8) + (digit_numbers[0]<< 16))
            device.midiOutMsg(0xB0 + (0x65 << 8) + (digit_numbers[0]<< 16))
            if len(minutes) == 3:
                device.midiOutMsg(0xB0 + (0x64 << 8) + (digit_numbers[minutes[2]]<< 16))
                device.midiOutMsg(0xB0 + (0x63 << 8) + (digit_numbers[minutes[1]]<< 16))
                device.midiOutMsg(0xB0 + (0x62 << 8) + (digit_numbers[minutes[0]]<< 16))

            if len(minutes) == 2:
                device.midiOutMsg(0xB0 + (0x64 << 8) + (digit_numbers[minutes[1]]<< 16))
                device.midiOutMsg(0xB0 + (0x63 << 8) + (digit_numbers[minutes[0]]<< 16))
                device.midiOutMsg(0xB0 + (0x62 << 8) + (digit_numbers[0]<< 16))
            if len(minutes) == 1:
                device.midiOutMsg(0xB0 + (0x64 << 8) + (digit_numbers[minutes[0]]<< 16))
                device.midiOutMsg(0xB0 + (0x62 << 8) + (digit_numbers[0]<< 16))
        else:
            device.midiOutMsg(0xB0 + (0x64 << 8) + (digit_numbers[0]<< 16))
            device.midiOutMsg(0xB0 + (0x63 << 8) + (digit_numbers[0]<< 16))
            device.midiOutMsg(0xB0 + (0x62 << 8) + (digit_numbers[0]<< 16))
            if len(minutes) == 2:
                device.midiOutMsg(0xB0 + (0x66 << 8) + (digit_numbers[minutes[1]]<< 16))
                device.midiOutMsg(0xB0 + (0x65 << 8) + (digit_numbers[minutes[0]]<< 16))
            if len(minutes) == 1:
                device.midiOutMsg(0xB0 + (0x66 << 8) + (digit_numbers[minutes[0]]<< 16))
                device.midiOutMsg(0xB0 + (0x65 << 8) + (digit_numbers[0]<< 16))
        old_minutes = minutes
        
    seconds = num_to_digits(playlist.getVisTimeStep()) #seconds
    if seconds != old_seconds:
        if len(seconds) > 1:
            device.midiOutMsg(0xB0 + (0x68 << 8) + (digit_numbers[seconds[1]]<< 16))
            device.midiOutMsg(0xB0 + (0x67 << 8) + (digit_numbers[seconds[0]]<< 16))
        else:
            device.midiOutMsg(0xB0 + (0x68 << 8) + (digit_numbers[seconds[0]]<< 16))
            device.midiOutMsg(0xB0 + (0x67 << 8) + (digit_numbers[0]<< 16))
        old_seconds = seconds

    if page_old != page:
        p = num_to_digits(page)
        if len(p) > 1:
            device.midiOutMsg(0xB0 + (0x61 << 8) + (digit_numbers[p[1]]<< 16))
            device.midiOutMsg(0xB0 + (0x60 << 8) + (digit_numbers[p[0]]<< 16))
        else:
            device.midiOutMsg(0xB0 + (0x61 << 8) + (digit_numbers[p[0]]<< 16))
            device.midiOutMsg(0xB0 + (0x60 << 8) + (digit_numbers[0]<< 16))
        page_old = page



def OnIdle():
    global is_sync
    global time_from_ak
    global get_resp
    global is_closing
    global connected

    if device.isAssigned() == 1:
        m = round(time.time() * 1000)
        if m - time_from_ak > 3000 and connected == True:
            print("disconected")
            OnDeInit()

        if is_sync == True and device.isAssigned() == 1:
            digits_display()
            send_alive()
            undo_led()
            function_led()
    else:
        OnDeInit()
    if ui.isClosing() == True:
        OnDeInit()

def function_led():
    global function_led_status
    
    for i in range(0,4):
        if function_led_status[i] != ui.getVisible(i):
            function_led_status[i] = ui.getVisible(i)
            if ui.getVisible(i) == 1:
                device.midiOutMsg(0x90 + (first_function_button + i << 8) + (0x02<< 16))
            else:
                device.midiOutMsg(0x90 + (first_function_button + i << 8) + (0x00<< 16))

def play_led():
    if transport.isPlaying() == True:
        device.midiOutMsg(0x90 + (0x5e << 8) + (0x01<< 16))
        device.midiOutMsg(0x90 + (0x5D << 8) + (0x00<< 16))
    else:
        device.midiOutMsg(0x90 + (0x5e << 8) + (0x00<< 16))
        device.midiOutMsg(0x90 + (0x5D << 8) + (0x02<< 16))

    
    
def refresh(val):
    # 0 all
    # 1 select
    # 2 faders
    # 3 mute
    # 4 arm
    # 5 solo
    # 6 screens
    # 7 pan
    ###print("refershing")
    global is_moving
    global page
    global fader_number
    global screen_names
    global screen_color
    global is_sync
    if is_sync == True and device.isAssigned() == 1:
            digits_display()
            send_alive()
            save_led()
            master()
            play_led()
            undo_led()
            function_led()
            for i in range(page,(page +fader_number)):
                if val == 1 or val == 0:
                    select(i)
                if val == 2 or val == 0:
                    faders(i)
                if val == 3 or val == 0:
                    mute(i)
                if val == 4 or val == 0:
                    arm(i)
                if val == 5 or val == 0:
                    solo(i)
                if val == 6 or val == 0:
                    screens(i)
                if val == 7 or val == 0:
                    pan(i)




def OnRefresh(event):
    refresh(0)