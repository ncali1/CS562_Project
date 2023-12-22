import subprocess
import sys

# Generate code for grouping variable calculation
def groupingVariable(predicates, aggregates, additionalCalulations): 
    return f"""
    cur.scroll(0,'absolute')

    for row in cur:
        # Look up current_row.cust in mf_struct
        pos = lookup(row, V, NUM_OF_ENTRIES, mf_struct)
        if {predicates}
            # Current_row.cust found in mf_struct
{aggregates}
    {additionalCalulations}"""

# Generate code for avg calculation
def additionalCalulations(addCalc): 
    return f"""for i in range(NUM_OF_ENTRIES):
        {addCalc}"""

# Split predicates for grouping var’s
# Ex: 1.state = 'NY'; 2.state = 'NJ'; 3.state = 'CT' -> [["state = 'NY'"], ["state = 'NJ'"], ["state = 'CT'"]
def splitPredicates(predicates, n):
    if predicates == ["None"]: # Edge case when there are no predicates
        return [[]]
    parsedPredicates = [[] for i in range(n)]
    for pred in predicates:
        try:
            index = int(pred[0]) - 1
            parsedPredicates[index].append(pred[2:])
        except:
            for list in parsedPredicates:
                list.append(pred)
    return parsedPredicates

# Generate the string for predicates in grouping variable calculation
# Ex: ["state = 'NY'"] -> cur['state'] == 'NY'
# Ex: [quant > avg_1_quant] -> cur['quant'] > mf_struct[pos][avg_1_quant]
def parsePredicates(predicates):
    compareAgg = set(["avg", "min", "max", "count", "sum"])
    predicateString = ""
    for pred in predicates:
        # Add an addition '=' for equality cases
        if pred.find(" = ") != -1:
            temp1 = pred.split(" ")
            temp2 = temp1[2].split("_")
            if temp2[0] in compareAgg: # For dependant aggregates (Assumes the aggregate has been calculated at this point in time)
                predicateString =  predicateString + " and row['" + temp1[0] + "'] == mf_struct[pos]['" + temp1[2] + "']"
            else:
                temp = pred.split(" ", 1)
                predicateString =  predicateString + " and row['" + temp[0] + "'] == " + temp[1][2:]
        else:
            temp1 = pred.split(" ")
            temp2 = temp1[2].split("_")
            if temp2[0] in compareAgg: # For dependant aggregates (Assumes the aggregate has been calculated at this point in time)
                predicateString =  predicateString + " and row['" + temp1[0] + "'] " + temp1[1] + " mf_struct[pos]['" + temp1[2] + "']"
            else:
                temp = pred.split(" ", 1)
                predicateString =  predicateString + " and row['" + temp[0] + "'] " + temp[1]
    if not predicateString:
        return "True:" # For the for loop to run
    else:
        return predicateString[5:] + ":" # Cut off the first and and add a colon

# Ex: ['count_1_quant', 'sum_2_quant', 'avg_2_quant', 'max_3_quant'] -> [[('count', 'quant', 'count_1_quant')], [('sum', 'quant', 'sum_2_quant'), ('avg', 'quant', 'avg_2_quant')], [('max', 'quant', 'max_3_quant')]]
def split_aggregates(aggregates):
        '''
        Usage: Used for splitting up the aggregates (a list of strings) into a list of lists of tuples (each list contains tuples composed of the aggregate followed by the attribute name)
        '''
        split_aggregates = [] # end result initialized
        curr_gv = "1" # assumes that the list of aggregates are sorted
        temp = []
        for agg in aggregates:
            split_agg = agg.split("_") # splits up the specific aggregate (as a string) (i.e. count_1_quant) into a list containing its components (i.e. ["count", "1", "quant"])
            if split_agg[1] != curr_gv:
                split_aggregates.append(temp)
                temp = []
                curr_gv = split_agg[1]
            temp.append((split_agg[0], split_agg[2], agg))
        split_aggregates.append(temp)
        return split_aggregates

def generate_agg_code(gv_list):
    '''
    Usage: Takes in gv_list (list of tuples) and generates the string that will be inputted into the generated file.
    '''
    agg_string = """"""
    avg_string = """"""
    for tup in gv_list: # tup is of the following type: (agg: String, attr: String)
        agg = tup[0]
        attr = tup[1]
        aggName = tup[2]
        # Will check to see which aggregate it is, will call the appropriate function that will return the appropriate string, which will get added to agg_string
        match agg:
            case 'count': 
                agg_string = agg_string + countCodeGenerator(aggName)
            case 'max':
                agg_string = agg_string + maxCodeGenerator(attr, aggName)
            case 'min':
                agg_string = agg_string + minCodeGenerator(attr, aggName)
            case 'sum':
                agg_string = agg_string + sumCodeGenerator(attr, aggName)
            case 'avg':
                string1, string2 = avgCodeGenerator(attr, aggName)
                agg_string = agg_string + string1
                avg_string = avg_string + string2
    return agg_string[:-1], avg_string # Can never have no aggregates

# Generates code for having clause
# Ex: sum_1_quant > 2 * sum_2_quant -> "if mf_struct[i]['sum_1_quant'] > 2 * mf_struct[i]['sum_2_quant']: _global.append(mf_struct[i])
def generate_having_code(having, groupByAttrib):
    having_string = "if"
    compareAgg = set(["avg", "min", "max", "count", "sum"])
    compareAttrib = set(groupByAttrib)
    wordList = having.split(" ")
    for word in wordList:
        temp = word.split("_")
        # Add a mf_struct[i] for aggregates and attributes
        if temp[0] in compareAgg or word in compareAttrib:
            having_string = having_string + " mf_struct[i]['" + word + "']"
        # Add an addition '=' for equality cases
        elif word == "=":
            having_string = having_string + " =="
        else:
            having_string = having_string + " " + word
    return having_string + ": _global.append(mf_struct[i])"

# Code generators for all of the aggregate functions
def maxCodeGenerator(attr, aggName):
    return f"""            if mf_struct[pos]['{aggName}'] == float('inf'): mf_struct[pos]['{aggName}'] = row['{attr}']\n            if row['{attr}'] > mf_struct[pos]['{aggName}']: mf_struct[pos]['{aggName}'] = row['{attr}']\n"""

def minCodeGenerator(attr, aggName):
    return f"""            if mf_struct[pos]['{aggName}'] == float('-inf'): mf_struct[pos]['{aggName}'] = row['{attr}']\n            if row['{attr}'] < mf_struct[pos]['{aggName}']: mf_struct[pos]['{aggName}'] = row['{attr}']\n"""

def countCodeGenerator(aggName):
    return f"""            mf_struct[pos]['{aggName}'] += 1\n"""

def sumCodeGenerator(attr, aggName):
    return f"""            mf_struct[pos]['{aggName}'] += row['{attr}']\n"""

def avgCodeGenerator(attr, aggName):
    return f"""            mf_struct[pos]['{aggName}'][0] += row['{attr}']\n            mf_struct[pos]['{aggName}'][1] += 1\n""", f"""mf_struct[i]['{aggName}'] =  mf_struct[i]['{aggName}'][0] / mf_struct[i]['{aggName}'][1]\n"""

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
        f.close()
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
        Pred_List = sys.argv[5] #  5. PRED-LIST – list of predicates for grouping
        Having = sys.argv[6] #  6. HAVING
    # Process Phi expression arguments
    S = S.split(", ")
    n = int(n)
    V = V.split(", ")
    F_Vect = F_Vect.split(", ")
    Pred_List = Pred_List.split("; ")
    splitPred = splitPredicates(Pred_List, n)
    splitAgg = split_aggregates(F_Vect)
    genCode = ""
    addCode = ""
    # Generate the loops for aggregate functions
    for i in range(n):
        parsePred = parsePredicates(splitPred[i])
        aggCode, avgCode = generate_agg_code(splitAgg[i])
        if avgCode:
            addCode = addCode + additionalCalulations(avgCode)
        genCode = genCode + groupingVariable(parsePred, aggCode, addCode)
        addCode = ""
    if Having == "None":
        havingCode = "_global.append(mf_struct[i])"
    else:
        havingCode = generate_having_code(Having, V)
    # Inject code in the appropriate variables

    functions = """
# Search for a given "group by" attrib. value(s) in mf_struct
def lookup(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for i in range(NUM_OF_ENTRIES):
        numSame = len(V)
        for attrib in V:
            if mf_struct[i][attrib] == cur_row[attrib]:
                numSame -= 1
            if numSame == 0:
                return i
    return -1

# Adds a new entry in mf_struct, corresponding to a newly found "group by" attrib. value
def add(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for attrib in V:
        mf_struct[NUM_OF_ENTRIES][attrib] = cur_row[attrib]
    NUM_OF_ENTRIES += 1
    return NUM_OF_ENTRIES, mf_struct
"""

    setUp = f"""
    S = {S} #  1. S - projected columns / expressions
    n = {n} #  2. n - number of grouping variables
    V = {V} #  3. V - grouping attributes
    F_Vect = {F_Vect} #  4. F-VECT - vector of aggregate functions
    Pred_List = {Pred_List} #  5. PRED-LIST - list of predicates for grouping
    Having = "{Having}" #  6. HAVING

    # Generate the code for mf_struct
    base_struct = dict()
    for attrib in V:
        base_struct[attrib] = None
    for aggre in F_Vect:
        split_agg = aggre.split("_")
        if split_agg[0] == 'avg':
            base_struct[aggre] = [0, 0] # Create a list to store sum and count to compute the average
        elif split_agg[0] == 'min':
            base_struct[aggre] = float('-inf')
        elif split_agg[0] == 'max':
            base_struct[aggre] = float('inf')
        else:
            base_struct[aggre] = 0
    mf_struct = []
    for i in range(500):
        mf_struct.append(copy.deepcopy(base_struct))
    NUM_OF_ENTRIES = 0

    # Populate mf-struct with distinct values of grouping attribute
    for row in cur:
        # Look up current_row.cust in mf_struct
        pos = lookup(row, V, NUM_OF_ENTRIES, mf_struct)
        if pos == -1:
            NUM_OF_ENTRIES, mf_struct = add(row, V, NUM_OF_ENTRIES, mf_struct)
    """

    # Note: The f allows formatting with variables.
    #       Also, note the indentation is preserved.
    tmp = f"""
import copy
import os
import psycopg2
import psycopg2.extras
import tabulate
from dotenv import load_dotenv

# DO NOT EDIT THIS FILE, IT IS GENERATED BY generator.py
{functions}

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
    {setUp}{genCode}
    for i in range(NUM_OF_ENTRIES):
        for col in set(F_Vect) - set(S):
            del mf_struct[i][col]
        {havingCode}
    
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
