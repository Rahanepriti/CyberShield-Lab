Objective

Create a vulnerable search page.

Attack

Used:
' OR '1'='1

Result

Retrieved all users from the database.

Fix

Replaced string concatenation with parameterized queries.

Lesson Learned

Never trust user input.
Always use prepared statements.
