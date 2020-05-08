# Integration of Nbgrader with Canvas

## create assignment

## create student version

    nbgrader assign 

## manual release and collect

### release
upload to canvas under the assignment


### collect

Download submitted assignmets for <lab> from Canvas. 

Uppgifter -> <lab> -> Ladda ner inlämningar

This will result in a downloaded file `submissions.zip`

Prepare the directory structure with

    mkdir -p downloaded/<lab>/archive
    cp submissions.zip !$

    nbgrader zip_collect <lab>

This step unpacks submissions.zip to

    downloaded/
    └── <lab>
        ├── archive
        │   └── submissions.zip
        └── extracted
            └── submissions
                ├── alidholeyleyla_23654_384397_<lab>.ipynb
                ├── allardsebastian_22468_396841_<lab>.ipynb
                ├── anderssonalma_22666_378861_<lab>.ipynb
                ...


and with the regex copies the individual student files to

    submitted/
    ├── 21076
    │   └── <lab>
    │       └── <lab>.ipynb
    ├── 21100
    │   └── <lab>
    │       └── <lab>.ipynb
    ├── 22468
    │   └── <lab>
    │       └── <lab>.ipynb
    ...

    
To grade is seems the students have to be properly registered in the database.


* export student info from "Omdömen" tab -> gives {date}.{course}...zip

use from tools/

```
$ ./tools/canvas2nbgrader {date}{course}.zip -> students.csv
$ nbgrader db student import students.csv
```


Now grade with , 

$ nbgrader autograde <lab>

