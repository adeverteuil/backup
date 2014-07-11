Feature: Backup a directory to another directory
    In order to maintain best practices in system administration
    As a system administrator
    I should be able to do regular backups

    Scenario: Do the first backup.
        Given the destination directory is empty
        When I invoke backup without parameters
        Then the program should exit 0
        And the destination directory should contain 1 hourly snapshot
