import subprocess
import sys

# Generate code for grouping variable calculation
def generate_for_loop_code(pred_string, agg_string, add_calc_string): 
    return f"""
    cur.scroll(0,'absolute')

    for row in cur:
        # Look up current_row.cust in mf_struct
        pos = lookup(row, V, NUM_OF_ENTRIES, mf_struct)
        if {pred_string}
            # Current_row.cust found in mf_struct
{agg_string}
    {add_calc_string}"""

# Generate code for avg calculation
def generate_avg_code(add_calc_string): 
    return f"""for i in range(NUM_OF_ENTRIES):
        {add_calc_string}"""

# Split predicates for grouping var’s
# Ex: "1.state = 'NY'; 2.state = 'NJ'"; 3.state = 'CT' -> [["state = 'NY'"], ["state = 'NJ'"], ["state = 'CT'"]]
# Ex: "1.state = 'NY or state = 'NJ'"; -> [["state = 'NY or state = 'NJ'"]]
def split_predicates(pred_list, n):
    if pred_list == ["None"]: # Edge case when there are no predicates
        return [[]]
    parsed_pred = [[] for i in range(n)]
    for pred in pred_list:
        try:
            index = int(pred[0]) - 1
            parsed_pred[index].append(pred[2:])
        except:
            for list in parsed_pred:
                list.append(pred)
    return parsed_pred

# Generate the string for predicates in grouping variable calculation
# Ex: ["state = 'NY'"] -> "row['state'] == 'NY'""
# Ex: ["quant > avg_1_quant"] -> "row['quant'] > mf_struct[pos][avg_1_quant]""
# Ex: ["month = 1 or month = 2"] -> "row['month'] == 1 or row['month'] == 2"
def generate_pred_code(pred_list):
    compare_agg = set(["avg", "min", "max", "count", "sum"])
    compare_attrib = set(["cust", "prod", "day", "month", "year", "state", "quant", "date"]) # Hard coded
    pred_string = ""
    for pred in pred_list:
        word_list = pred.split(" ")
        for word in word_list:
            temp = word.split("_")
            if temp[0] in compare_agg: # Add mf_struct[pos] for dependant aggregates (Assumes the aggregate has been calculated at this point in time)
                pred_string = pred_string + " mf_struct[pos]['" + word + "']"
             # Add an additional '=' for equality cases
            elif word == "=":
                pred_string = pred_string + " =="
            # Add row for attributes
            elif word in compare_attrib:
                pred_string = pred_string + " row['" + word + "']"
                print(pred_string)
            else:
                pred_string = pred_string + " " + word
        # Add implied and
        pred_string = pred_string + " and"
    if not pred_string:
        return "True:" # For the for loop to run
    else:
        return pred_string[1:-4] + ":" # Cut off the extra first space, the last and, and add a colon

# Ex: ['count_1_quant', 'sum_2_quant', 'avg_2_quant', 'max_3_quant'] -> [[('count', 'quant', 'count_1_quant')], [('sum', 'quant', 'sum_2_quant'), ('avg', 'quant', 'avg_2_quant')], [('max', 'quant', 'max_3_quant')]]
def split_aggregates(agg_list):
        '''
        Usage: Used for splitting up the aggregates (a list of strings) into a list of lists of tuples (each list contains tuples composed of the aggregate followed by the attribute name)
        '''
        split_aggregates = [] # End result initialized
        curr_gv = "1" # Assumes that the list of aggregates are sorted
        temp = []
        before_agg = []
        for agg in agg_list:
            split_agg = agg.split("_") # Splits up the specific aggregate (as a string) (i.e. count_1_quant) into a list containing its components (i.e. ["count", "1", "quant"])
            if split_agg[1] != curr_gv:
                split_aggregates.append(temp)
                temp = []
                curr_gv = split_agg[1]
            if len(split_agg) == 2:
                before_agg.append((split_agg[0], split_agg[1], agg))
                continue
            temp.append((split_agg[0], split_agg[2], agg))
        split_aggregates.append(temp)
        return split_aggregates, before_agg

# Ex:
def generate_agg_code(gv_list):
    '''
    Usage: Takes in gv_list (list of tuples) and generates the string that will be inputted into the generated file.
    '''
    agg_string = """"""
    avg_string = """"""
    for tup in gv_list: # tup is of the following type: (agg: String, attr: String)
        agg = tup[0]
        attrib = tup[1]
        agg_name = tup[2]
        # Will check to see which aggregate it is, will call the appropriate function that will return the appropriate string, which will get added to agg_string
        match agg:
            case 'count': 
                agg_string = agg_string + count_code_generator(agg_name)
            case 'max':
                agg_string = agg_string + max_code_generator(attrib, agg_name)
            case 'min':
                agg_string = agg_string + min_code_generator(attrib, agg_name)
            case 'sum':
                agg_string = agg_string + sum_code_generator(attrib, agg_name)
            case 'avg':
                in_loop_string, out_loop_string = avg_code_generator(attrib, agg_name)
                agg_string = agg_string + in_loop_string
                avg_string = avg_string + out_loop_string
    return agg_string[:-1], avg_string # Can never have no aggregates

# Generates code for having clause
# Ex: "sum_1_quant > 2 * sum_2_quant" -> "if mf_struct[i]['sum_1_quant'] > 2 * mf_struct[i]['sum_2_quant']: _global.append(mf_struct[i])
def generate_having_code(having, group_by_attrib):
    having_string = "if"
    compare_agg = set(["avg", "min", "max", "count", "sum"])
    compare_attrib = set(group_by_attrib)
    word_list = having.split(" ")
    for word in word_list:
        temp = word.split("_")
        # Add a mf_struct[i] for aggregates and attributes
        if temp[0] in compare_agg or word in compare_attrib:
            having_string = having_string + " mf_struct[i]['" + word + "']"
        # Add an additional '=' for equality cases
        elif word == "=":
            having_string = having_string + " =="
        else:
            having_string = having_string + " " + word
    return having_string + ": _global.append(mf_struct[i])"

# Code generators for all of the aggregate functions
def max_code_generator(attrib, agg_name):
    return f"""            if mf_struct[pos]['{agg_name}'] == float('inf'): mf_struct[pos]['{agg_name}'] = row['{attrib}']\n            if row['{attrib}'] > mf_struct[pos]['{agg_name}']: mf_struct[pos]['{agg_name}'] = row['{attrib}']\n"""

def min_code_generator(attrib, agg_name):
    return f"""            if mf_struct[pos]['{agg_name}'] == float('-inf'): mf_struct[pos]['{agg_name}'] = row['{attrib}']\n            if row['{attrib}'] < mf_struct[pos]['{agg_name}']: mf_struct[pos]['{agg_name}'] = row['{attrib}']\n"""

def count_code_generator(agg_name):
    return f"""            mf_struct[pos]['{agg_name}'] += 1\n"""

def sum_code_generator(attrib, agg_name):
    return f"""            mf_struct[pos]['{agg_name}'] += row['{attrib}']\n"""

def avg_code_generator(attrib, agg_name):
    return f"""            mf_struct[pos]['{agg_name}'][0] += row['{attrib}']\n            mf_struct[pos]['{agg_name}'][1] += 1\n""", f"""mf_struct[i]['{agg_name}'] =  mf_struct[i]['{agg_name}'][0] / mf_struct[i]['{agg_name}'][1]\n"""

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
    split_pred = split_predicates(Pred_List, n)
    split_agg, before_agg = split_aggregates(F_Vect)
    gen_code = ""
    add_code = ""
    # Generate the loop for general aggregate functions that are depended on
    if before_agg:
        parse_pred = generate_pred_code([])
        agg_code, avg_code = generate_agg_code(before_agg)
        if avg_code:
            add_code = add_code + generate_avg_code(avg_code)
        gen_code = gen_code + generate_for_loop_code(parse_pred, agg_code, add_code)
        add_code = ""
    # Generate the loops for aggregate functions
    for i in range(n):
        parse_pred = generate_pred_code(split_pred[i])
        agg_code, avg_code = generate_agg_code(split_agg[i])
        if avg_code:
            add_code = add_code + generate_avg_code(avg_code)
        gen_code = gen_code + generate_for_loop_code(parse_pred, agg_code, add_code)
        add_code = ""
    if Having == "None":
        having_code = "_global.append(mf_struct[i])"
    else:
        having_code = generate_having_code(Having, V)
    # Inject code in the appropriate variables

    functions = """
# Search for a given "group by" attrib. value(s) in mf_struct
def lookup(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for i in range(NUM_OF_ENTRIES):
        num_same = len(V)
        for attrib in V:
            if mf_struct[i][attrib] == cur_row[attrib]:
                num_same -= 1
            if num_same == 0:
                return i
    return -1

# Adds a new entry in mf_struct, corresponding to a newly found "group by" attrib. value
def add(cur_row, V, NUM_OF_ENTRIES, mf_struct):
    for attrib in V:
        mf_struct[NUM_OF_ENTRIES][attrib] = cur_row[attrib]
    NUM_OF_ENTRIES += 1
    return NUM_OF_ENTRIES, mf_struct
"""

    set_up = f"""
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
    for agg in F_Vect:
        split_agg = agg.split("_")
        if split_agg[0] == 'avg':
            base_struct[agg] = [0, 0] # Create a list to store sum and count to compute the average
        elif split_agg[0] == 'min':
            base_struct[agg] = float('-inf')
        elif split_agg[0] == 'max':
            base_struct[agg] = float('inf')
        else:
            base_struct[agg] = 0
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
    {set_up}{gen_code}
    for i in range(NUM_OF_ENTRIES):
        for col in set(F_Vect) - set(S):
            del mf_struct[i][col]
        {having_code}
    
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
