# gfm
Gmail Filer Manager using YAML format.

## Installation


## Usage

### extract

`extract` command converts mailFilters.xml, which can be exported from Gmail,
to YAML format.

Default input name is **mailFilters.xml**.
Default ouput name is **mailFilters.yaml**.

They can be changed by arguments:

    $ gfm extract [input name [output name]]

Once you have YAML file,
you can edit it and use it as an input for `gfm make`.

### make

`make` command makes XML of filters to be imported in Gmail.

Input is YAML format.

Default input name is **mailFilters.yaml**.
Default ouput name is **mailFilters.yaml**.

```yaml
filters:
- from: "foo@example.com"
  lable: "foo"
- subject: "[test]"
  lable: "test"
  shouldMarkAsRead: "true"
namespaces:
  apps: http://schemas.google.com/apps/2006
  atom: http://www.w3.org/2005/Atom
```

**namespaces** can be omitted.
It is included if you use `gfm extract`,
but it will be automatically added by `gfm make` even if is omitted.

## Filter properties

### Filter Criteria Properties

Name|XML attribute|Description
:---|:------------|:----------
From|name="from"|The email comes from this address.
To|name="to"|The email is sent to this address.
Subject|name="subject"|The email's title includes this value.
Has the words|name="hasTheWord"|The email has this value (search operators).
Doesn't have|name="doesNotHaveTheWord"|The email doesn't have this value (search operators).
Has attachment|name="hasAttachment"|true or false for if the email has attachments.
Don't include chats|name="excludeChats"|true or false for if the email includes chats.
Size|name="size"|The email size. If it is specified, the mail size is compared to this value with sizeOperator and sizeUnit.
Size operator|name="sizeOperator"|s_sl (larger than) or s_ss (smaller than).
Size unit|name="sizeUnit"|Unit of email size: s_sb (B), s_skb (kB) or s_smb (MB).

**hasTheWord** and **doesNotHaveTheWord** are search operators.
Such a label can be specified here.

Please check following help for more details:

> [Search operators you can use with Gmail - Gmail Help](https://support.google.com/mail/answer/7190)

### Filter Action Properties

Name|XML attribute|Description
:---|:------------|:----------
Skip the Inbox (Archive it)|name="shouldArchive"
Mark as read|name="shouldMarkAsRead"|
Star it|name="shouldStar"|
Apply the label|name="label"|
Forward it to|name="forwrdTo"
Delete it|name="shouldTrash"|
Never send it to Spam|name="shouldNeverSpam"|
Always mark it as important|name="shouldAlwaysMarkAsImportant"|
Never mark it as important|name="shouldNeverMarkAsImportant"|
Categorize as|name="smartLabelToApply"|Add smart label. value can be "^smartlabel_personal", "^smartlabel_social", "^smartlabel_promo", "^smartlabel_group" or "^smartlabel_notification".

Tips:

You can use array for **label** to set several labels on the same criteria.

## Filter in API

> [Users.settings.filters  Gmail API  Google Developers](https://developers.google.com/gmail/api/v1/reference/users/settings/filters#resource-representations)

> [Managing Filters  Gmail API  Google Developers](https://developers.google.com/gmail/api/guides/filter_settings)

### Filter Criteria in API

Name|Action|Description
:---|:------------|:----------
From|from|The email comes from this address.
To|to|The email is sent to this address.
Subject|subject|The email's title includes this value.
Has the words|query|The email has this value (search operators).
Doesn't have|negatedQuery|The email doesn't have this value (search operators).
Has attachment|hasAttachment|true or false for if the email has attachments.
Don't include chats|excludeChats|true or false for if the email includes chats.
Size|size|The email size (in byte). If it is specified, the mail size is compared to this value with sizeOperator.
Size operator|sizeComparison|larger (larger than) or smaller (smaller than).
Size unit|NOT USED|In API, size is always byte. To use MB, just give size of 10,000,000 for 10MB.


### Filter Action in API

Name|Action|Description
:---|:------------|:----------
Skip the Inbox (Archive it)|removeLabelIds|Put "INBOX" in value's array.
Mark as read|removeLabelIds|Put "UNREAD" in value's array.
Star it|addLabelIds|Put "STARRED" in value's array.
Apply the label|addLabelIds|Put user label id (NOT label name) in value's array.
Forward it to|forward|put email address, to which email should be forwarded, in value.
Delete it|addLabelIds|Put "TRASH" in value's array.
Never send it to Spam|removeLabelIds|Put "SPAM" in value's array.
Always mark it as important|addLabelIds|Put "IMPORTANT" in value's array.
Never mark it as important|removeLabelIds|Put "IMPORTANT" value's array.
Categorize as|addLabelIds|Add smart label. Value can be "CATEGORY_PERSONAL", "CATEGORY_SOCIAL", "CATEGORY_PROMO", "CATEGORY_GROUP" or "CATEGORY_NOTIFICATION".

## How to export/import filters

Check **Export or import filters** in the official help:

> [Create rules to filter your emails - Gmail Help](https://support.google.com/mail/answer/6579)

## Filter Tips

### Numbering labels

Gmail's labels are sorted automatically.

But you may want to put some labels such **Work**, which is always at the bottom,
on the top.

To do it, you can set prefix numbers on labels.

- 01_Work
- 02_Private
- 03_Others

Then, these labels are listed in this order.

### Use labels like folder

Gmail has only **label**, but some other mail clients have **folder**.

* Label: User can set several labels on the same message.
* Folder: A message is included only in one folder.

And all filters are always applied to the new mail.

In this case, if the mail is caught by several filters for labels,
several labels are set.

To avoid several labels to use it as **folder**,
**has:nouserlabels** keyword is useful.

If **hasTheWord** includes this keyword,
only the mail which still does not have the label can be caught.

e.g.)

    filters:
    - hasTheWord: "from:foo@example.com"
      label: "00_foo"
    - hasTheWord: "has:nouserlabels from:example.com"
      label: "01_example"
      shouldArchive: "true"
    - hasTheWord: "has:nouserlabels"
      label: "09_others"
      shouldArchive: "true"

These filters put a label **foo** for mails from **foo@example.com**,
and put a label **example** for mails from **example.com** domain other than **foo@example.com**.
In addition, if it is not from **foo**, the mail is archived.

And the last filter send other mails to **others** label,
and skip the Inbox.
Such a filter make you free from notification bombs
in the Gmail app of a cell phone.

To use such filters, the order is important.

Note: If you modify filters in the Gmail web interface,
the order is changed: the modified one goes to the bottom.

This is one of the reasons why I wanted these scripts.

### Use DummyInbox to leave only specific mails in the Inbox

You may have more labels with which mails must skip the Inbox.

In this case, **DummyInbox** method label can be used instead of
setting **shouldArchive: "true"** for filters.

The setting is like this:

    filters:
    - hasTheWord: "from:foo@example.com"
      label:
      - "00_foo"
      - "99_DummyInbox"
    - hasTheWord: "from:example.com"
      label:
      - "01_example"
      - "99_DummyInbox"
    - hasTheWord: "from:example2.com"
      label: "02_example2"
    - hasTheWord: "from:example3.com"
      label: "03_example3"
    - hasTheWord: "from:example4.com"
      label: "04_example4"
    - hasTheWord: "from:example5.com"
      label: "05_example5"
    - hasTheWord: "has:nouserlabels"
      label: "09_others"
    - hasTheWord: "-label:99_DummyInbox"
      shouldArchive: "true"

This setting put additional **99_DummyInbox** label
to which you want to remain in the Inbox.

And the final filter archives mails without **99_DummyInbox** label.

In the above setting, **has:nouserlabels** is not used for **from:example.com**.
Therefore the mail from **foo@example.com** has two labels.

The main difference from
[Use labels like folder](https://github.com/rcmdnk/gmail_filter_manager#use-labels-like-folder) method
is that you can put two different labels between them archive policies are different.

If **shouldArchive** is in the each label, all mails associated to the label are archived.
But this method can remain what you want easily.

In addition, only the order of the filters can be free other than the last label,
so that it makes easy to modify with the web interface.
Although you still need to "modify"
**hasTheWord: "-label:99_DummyInbox"** filter after any other filter changes...
(such adding one space in **Has the words** and save, and remove the space and save again...)

## References

* [gmail_filter_manager: GmailのフィルタをYAMLで簡単に管理する](https://rcmdnk.com/blog/2018/07/07/computer-gmail-python/)
