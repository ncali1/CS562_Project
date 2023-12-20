import subprocess
import sys
import copy

# Search for a given “group by” attrib. value(s) in mf_struct
def lookup(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for i in range(NUM_OF_ENTRIES):
        numSame = len(V)
        for attrib in V:
            if mf_struct[i][attrib] == cur_row[attrib]:
                numSame -= 1
            if numSame == 0:
                return i
    return -1

# Adds a new entry in mf_struct, corresponding to a newly found “group by” attrib. value
def add(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for attrib in V:
        mf_struct[NUM_OF_ENTRIES][attrib] = cur_row[attrib]
    NUM_OF_ENTRIES += 1
    return NUM_OF_ENTRIES

def main():
    """
    This is the generator code. It should take in the MF structure and generate the code
    needed to run the query. That generated code should be saved to a 
    file (e.g. _generated.py) and then run.
    """
    # Reading input
    """
    Usage:  python generator.py <.txt>
    Ex:     See example.txt
    """
    if len(sys.argv) == 2: # From file
        f = open(sys.argv[1], "r")
        S = f.readline()
        n = f.readline()
        V = f.readline()
        F_Vect = f.readline()
        Pred_List = f.readline()
        Having = f.readline()
        S = S.strip("\n")
        n = n.strip("\n")
        V = V.strip("\n")
        F_Vect = F_Vect.strip("\n")
        Pred_List = Pred_List.strip("\n")
        Having = Having.strip("\n")
    """
    Usage:  python generator.py <S> <n> <V> <F_Vect> <Pred_List> <Having>
    Ex:     python generator.py "cust, count_1_quant, sum_2_quant, max_3_quant" 3 cust "count_1_quant, sum_2_quant, avg_2_quant, max_3_quant" "1.state = 'NY'; 2.state = 'NJ'; 3.state = 'CT'" None
    """
    if len(sys.argv) == 7: # From command line
        S = sys.argv[1] #  1. S - projected columns / expressions
        n = sys.argv[2] #  2. n - number of grouping variables
        V = sys.argv[3] #  3. V - grouping attributes
        F_Vect = sys.argv[4] #  4. F-VECT – vector of aggregate functions
        Pred_List = sys.argv[5] # 5. PRED-LIST – list of predicates for grouping
        Having = sys.argv[6] # 6. HAVING
    # Process Phi expression arguments
    S = S.split(", ")
    n = int(n)
    V = V.split(", ")
    F_Vect = F_Vect.split(", ")
    Pred_List = Pred_List.split("; ")
    # Having unsure about the format of the input
    # Generate the code for mf_struct
    base_struct = {}
    for attrib in V:
        base_struct[attrib] = None
    for aggre in F_Vect:
        base_struct[aggre] = 0
    mf_struct = []
    for i in range(500):
        mf_struct.append(copy.deepcopy(base_struct))
    NUM_OF_ENTRIES = 0
    # Populate mf-struct with distinct values of grouping attribute

    '''

    ############################################################################################
    # READ INPUT (READING FROM FILE)
    

    # READ INPUT (INTERACTIVELY FROM USER)
        

    # CREATING MF STRUCT


    # ANY UPKEEP STEPS REQUIRED


    ####### START OF QUERY PROCESSING #######
    # QUERY PROCESSING LOGIC (NEEDS TO BE INSERTED INTO body VARIABLE (SEE BELOW))
    ## (NOTE 0) SHOULD BE IN A BIG FOR-LOOP (JAKOB), iterate through vector of aggregates (#4 in phi args)

    ## MAX (FOR LOOP)
    # initialize dictionary
    ## i think that the name of the dictionary should be different for each max computation since there could be more than one, and we don't want things to get messy. name it as AGG_NAME_dict, where AGG_NAME is where in the vector of aggregates we are currently at (see NOTE 0 of Query Processing Logic)
    # max_val = row0_val # set the max to be the value of the very first NOT NEEDED IF USE DICT, SINCE YOU CAN ALWAYS ADD TO DICT NEW VALUES
    for row in database: # specific variable names tbd
        if where_clause_conditions:
            group_tuple = blablaba # this is to calculate where in the dictionary we are going to compare with (or add) adding might need separate code, idk
            if value_at_row > max_val_for_group: # max_val_for_group is gonna be stored in the dict
                max_val_for_group = value # this needs to be changed for the given dict entry for that tuple
        # Question: ~~do we need to keep track of the rows in a separate thing so that we can display them all~~
        ## Answer: we do not, since we will likely be keeping the max value in a dictionary, where the key is the grouping tuple (e.g. (cust, prod)) and the value is the max for that tuple (like, if we were looking for the max quantity for each customer and product combination, then the dict would be like {(Boo, Apple): 500; (Boo, Banana): 1000 ...}), or something like that (formatting tbd)

    ## MIN (FOR LOOP)
    # symmetric to max

    ## COUNT (FOR LOOP)
    # similar to max?


    ## SUM (FOR LOOP)
    # similar to max?

    ## AVERAGE (FOR LOOP) (RELIES ON COUNT AND SUM)
    # similar to max?

    ''' 
    ####### END OF QUERY PROCESSING ####### 

    # INJECT FOR LOOPS INTO body VARIABLE


    ############################################################################################
    """
    for row in cur:
        if row['quant'] > 10:
            _global.append(row)
    """
    body = f"""
    S = {S}
    n = {n}
    V = {V}
    F_Vect = {F_Vect}
    Pred_List = {Pred_List}
    Having = {Having}
    """

    # Note: The f allows formatting with variables.
    #       Also, note the indentation is preserved.
    tmp = f"""
import os
import psycopg2
import psycopg2.extras
import tabulate
from dotenv import load_dotenv

# DO NOT EDIT THIS FILE, IT IS GENERATED BY generator.py

def query():
    load_dotenv()

    user = os.getenv('USER')
    password = os.getenv('PASSWORD')
    dbname = os.getenv('DBNAME')

    conn = psycopg2.connect("dbname="+dbname+" user="+user+" password="+password,
                            cursor_factory=psycopg2.extras.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales")
    
    _global = []
    {body}
    
    return tabulate.tabulate(_global,
                        headers="keys", tablefmt="psql")

def main():
    print(query())
    
if "__main__" == __name__:
    main()
    """

    # Write the generated code to a file
    open("_generated.py", "w").write(tmp)
    # Execute the generated code
    subprocess.run(["python", "_generated.py"])


if "__main__" == __name__:
    main()
