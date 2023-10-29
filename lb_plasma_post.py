import configparser
import argparse,sys
 
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser = argparse.ArgumentParser()

error = False
error_msg = ""

param_file_default = "params.ini" #the default file name we look for if the param file isn't provided as a parameter

default_outfile_prefix = "lbp_"

def add_error_msg(msg):
    global error, error_msg
    error= True
    error +=msg


def get_command_line_arguments():

    parser.add_argument("--infile", help="input filename to parse, must be lightburn GRBL-M3 generated")
    parser.add_argument("--outfile", help="output filename to generated, should be different to input filename")
    parser.add_argument("--paramfile", help="paramaters .ini filename to use")

    args={}
    args=parser.parse_args()

    return args 


def read_config_param(section, param):
    val=""
    
    #check if the param value is set
    if config.has_option(section, param):
        val = config.get(section, param)  
    else:
        #required value not set, set error message
        add_error_msg("["+section+"]\n"+param+ "=Not Set \n")
        
    #return the parameter value
    return val


def read_params(params_file, commandline_args):
    param_vals = {}

    #open the params file
    try:
        with open(params_file) as p:
            config.read_file(p)
    except IOError:

        #param file could not be opened
        add_error_msg("ERROR: Could not open parameter file '" + params_file+"'")
        return

    #commandline args take precident over param file values

    #input file- check if the input file was provided as a command line argument
    if(commandline_args.infile is None):

        #no input file given as command line argument, read from param file instead
        param_vals["file_input"] = read_config_param("files", "file_input")
    else:
        param_vals["file_input"] = commandline_args.infile
    
    #check if output file was given as argument
    if(commandline_args.outfile is None):

        #output file not given as argument, attempt to read it from params file
        if config.has_option("files","file_output"):

            #output file exists in params file
            param_vals["file_output"]  = config.get("files","file_output")
        else:

            #no output file exists in params file, use the default outputfile
            param_vals["file_output"] = default_outfile_prefix + param_vals["file_input"]
            print("INFO: No output file specified, using default file name " +param_vals["file_output"] )
    else:

        #output file given as command line argument  
        param_vals["file_input"] = commandline_args.outfile

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

    code_replace = {
        "M3" :  param_vals["M3_replace"] ,  
        "M5" :  param_vals["M5_replace"]   
    }
    
    #open the files
    try:
        ifile = open(param_vals["file_input"], 'r')
    except FileNotFoundError:
        add_error_msg("ERROR: couldn't open input file '" + param_vals["file_input"] +"'" )
        return

    try:
        ofile = open(param_vals["file_output"], 'w') 
    except FileNotFoundError:
        add_error_msg("ERROR: couldn't open output file '" + param_vals["file_output"] +"'" )
        return
    
    print("INFO: Using input file " + param_vals["file_input"])
    print("INFO: Using output file " + param_vals["file_output"])

    #skip the first M5 command in the generated gcode
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

def main():

    #get the command line arguments, note these take priority over the param file values
    command_args = get_command_line_arguments()

    #read the parameter file values
    params = {}

    #use the default parameter file name value if one is not specified in the command line arguments
    param_file = param_file_default
    
    #check if parameter file was given as a command line argument
    if command_args.paramfile is not None:

        #use the parameter filename given as a command line argument
        param_file = command_args.paramfile

    print("INFO: Using parameter file " + param_file)
    
    #read the parameter file
    params = read_params(param_file,command_args)
    
    #check for errors reading the parameter file
    if(error == True):
        print("The following errors occured")
        print(error_msg)
    else:

        #no errors reading the parameter file, attempt to write the post file
        write_post(params)

        #check for errors writing the processed file
        if(error == True):
            print("The following errors occured")
            print(error_msg)
        else:
            #all good
            print("Completed: " + params["file_output"] + " created ok")



main()

