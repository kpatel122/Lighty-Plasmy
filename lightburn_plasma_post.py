import configparser
 
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

error = False
error_msg = ""

params ={}


def read_config_param(section, param):
    global error, error_msg
    
    val=""
    if config.has_option(section, param):
        val = config.get(section, param) #config.get(section, param)
    else:
        error = True
        error_msg += "["+section+"]\n"+param+ "=Not Set \n"
    
    return val


def read_params(params_file):

    param_vals = {}

    config.read(params_file)

    #file values
    param_vals["file_input"] = read_config_param("files", "file_input")
    param_vals["file_output"] = read_config_param("files", "file_output")

    #probe values
    param_vals["probe_feed"] = read_config_param("probe", "probe_feed")
    param_vals["probe_distance"] = read_config_param("probe", "probe_distance")
    param_vals["probe_z_value_at_hit"] = read_config_param("probe", "probe_z_value_at_hit")

    #retract values
    param_vals["probe_retract_feed"] = read_config_param("retract", "probe_retract_feed")
    param_vals["probe_retract_distance"] = read_config_param("retract", "probe_retract_distance")

    #dwell values
    param_vals["dwell_start_time"] = read_config_param("dwell", "dwell_start_time")
    param_vals["dwell_end_time"] = read_config_param("dwell", "dwell_end_time")

    #gcode
    m3_replace = read_config_param("gcode_replace", "M3")
    m5_replace = read_config_param("gcode_replace", "M5") 

    #add new lines so this block is slightly seperated from the rest of the gcode and is therefore easier to find and verify
    param_vals["M3_replace"] = str("\n;M3 Replacement\n" + m3_replace + "\n")

    param_vals["M5_replace"] = str("\n;M5 Replacement\n" + m5_replace + "\n")

    return param_vals



def write_post(param_vals):

    #probe_gcode = "\n;touch off \nG32.2 Z" + param_vals["probe_distance"] + " F"+ param_vals["probe_feed"] +" ;probe the torch \nG92 Z0 ;set 0\n" 
    #retract_gcode = "G1 Z"+param_vals["probe_retract_distance"] +" F" +param_vals["probe_retract_feed"] +  ";retract the torch\n"
    
    #dwell_start_gcode = ""
    #if(param_vals["dwell_start_time"] !="0"):
    #    dwell_start_gcode="G4 P"+param_vals["dwell_start_time"] +";dwell start\n"
    
    #dwell_end_gcode=";dwell end\n"

    code_replace = {
        "M3" :  param_vals["M3_replace"] , #"M3" : probe_gcode + retract_gcode + "M3 ;turn on torch\n" + dwell_start_gcode,
        "M5" :  param_vals["M5_replace"]  #needs further testing
    }
    
    #text_to_search = "M3"
    #text_to_replace=probe_gcode+retract_gcode



    #open the files
    ifile = open(param_vals["file_input"], 'r')
    ofile = open(param_vals["file_output"], 'w') 
    
    first_m5 = True
    

    #loop until EOF     
    while True:
        #read the file line as a string
        line = ifile.readline() 
        
        #check the file has not reached the end
        if line:

            #set comments to blank
            out_line_comments = ""
            line_has_comments = False

            #store the current line
            gcode_line = line.split(";")
            
            #the line without the comments
            out_line = gcode_line[0] 

            #check if the current line has comments
            if(len(gcode_line) > 1):
                out_line_comments = gcode_line[1]
                line_has_comments = True
                
                #if the line contains only comments, write it and move on
                if (out_line == "") and (line_has_comments == True):
                    ofile.write(";" + out_line_comments)
                    continue

            #the line contains gcode remove leading white spaces
            out_line = out_line.lstrip(" ") 

            #ignore the first M5 that lightburn puts out as it isn't closing an M3
            if first_m5 == True:
                if( str(out_line[0] + out_line[1]).upper() == "M5" ): #found the first M5, do not replace
                    first_m5 = False
                    if(line_has_comments == True):
                        ofile.write(out_line + "; " + out_line_comments) #keep the line the same
                    else:
                        ofile.write(out_line)
                    continue

            #replace the M3 command with the touch off command
            for key in code_replace:
                if(key in out_line.upper()): #check if M command is in the current line

                    #replace the gcdoe M command with the one specified in params and exit the loop
                    out_line = out_line.upper().replace(key, code_replace[key])
                    break
            
            #write the line to the output file
            if(line_has_comments == True): #write the line with comments
                ofile.write(out_line+ "; " + out_line_comments)
            else:
                ofile.write(out_line) #write the gcode line only
        else:
            break #reached EOF
        

    #close the files
    ifile.close()
    ofile.close()

params = read_params("params.ini")

if(error == True):
    print("The following errors occured")
    print(error_msg)
else:
    write_post(params)
    print("Completed: " + params["file_output"] + " created ok")


 
