* what i built:
    models.py source.py storage.py test_ingest.py test_storage.py
* concept i acctualy learnt:
    Basesetting, Producer and Connectors in Python. what * do in different condition. datetype should have a fallback policy. 
    Modules should not do work on import. 
    database actions should be in one storage class instead of using loose database functions.
    Testing without the network (DI + mocking)
    python context manager, ie: when use storage as s, it will automatilly run functions like __exit__ inside the class.
    Natural vs. surrogate key. use URL identifies an araitcle not auto generate DB id.
    SQL injection / parameterized querie: use ? place holder instead of string formatting in sql actions. security matters.
* What tripped me up: 
    Forget set up fallback policy. datatype in connector and producer should be coherrent.
    
* Honest notes: learnt how to passing argument in various ways in Python. all thest should go to test_**.py istead of use print at module level.