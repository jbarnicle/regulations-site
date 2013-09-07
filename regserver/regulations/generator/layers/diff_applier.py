import types
import copy
from collections import deque
import tree_builder


class DiffApplier(object):
    """ Diffs between two versions of a regulation are represented in our
    particular JSON format. This class applies that diff to the older version
    of the regulation, generating HTML that clearly shows the changes between
    old and new. """

    INSERT = u'insert'
    DELETE = u'delete'
    DELETED_OP = 'deleted'
    ADDED_OP = 'added'

    def __init__(self, diff_json, label_requested):
        self.diff = diff_json
        #label_requested is the regulation label for which a diff is 
        #requested. 
        self.label_requested = label_requested

    def deconstruct_text(self, original):
        self.oq = [deque([c]) for c in original]

    def insert_text(self, pos, new_text):
        if pos == len(self.oq):
            self.oq[pos-1].extend(['<ins>', new_text, '</ins>'])
        else:
            self.oq[pos].extend(['<ins>', new_text, '</ins>'])

    def delete_text(self, start, end):
        self.oq[start].appendleft('<del>')
        self.oq[end-1].append('</del>')

    def get_text(self):
        return ''.join([''.join(d) for d in self.oq])

    def delete_all(self, text):
        """ Mark all the text passed in as deleted. """
        return '<del>' + text + '</del>'

    def add_all(self, text):
        """ Mark all the text passed in as deleted. """
        return '<ins>' + text + '</ins>'

    def add_nodes_to_tree(self, original, adds):
        """ Add all the nodes from new_nodes into the original tree. """
        tree = tree_builder.build_tree_hash(original)

        for label, node in adds.queue:
            p_label = tree_builder.parent_label(label)
            if tree_builder.parent_in_tree(p_label, tree):
                tree_builder.add_node_to_tree(node, p_label, tree)
                adds.delete(label)
            else:
                parent = adds.find(p_label)
                if parent:
                    tree_builder.add_child(parent[1], node)
                else:
                    original.update(node)

    def tree_changes(self, original_tree):
        """ Apply additions to the regulation tree. """

        def relevant_added(label):
            """ Get the operations that add nodes, for the requested section/pargraph. """
            if self.diff[label]['op'] == self.ADDED_OP and label.startswith(self.label_requested):
                return True

        def node(diff_node, label):
            """ Take diff's specification of a node, and actually turn it into a regulation node. """
            node = copy.deepcopy(diff_node)
            node['label_id'] = label
            node['children'] = []
            if node['title'] is None:
                del node['title']
            return node

        new_nodes = [(label, node(self.diff[label]['node'], label)) for label in self.diff if relevant_added(label)]
        reg_text_nodes = [l for l in new_nodes if 'Interp' not in l[0]]

        adds = tree_builder.AddQueue()
        adds.insert_all(reg_text_nodes)

        tree = self.add_nodes_to_tree(original_tree, adds)
        return tree


    def apply_diff(self, original, label):
        if label in self.diff:
            if self.diff[label]['op'] == self.DELETED_OP:
                return self.delete_all(original)
            if self.diff[label]['op'] == self.ADDED_OP:
                return self.add_all(original)
            if 'text' in self.diff[label]:
                text_diffs = self.diff[label]['text']
                self.deconstruct_text(original)

                for d in text_diffs:
                    if d[0] == self.INSERT:
                        _, pos, new_text = d
                        self.insert_text(pos, new_text + ' ')
                    if d[0] == self.DELETE:
                        _, s, e = d
                        self.delete_text(s, e)
                    if isinstance(d[0], types.ListType):
                        if d[0][0] == self.DELETE and d[1][0] == self.INSERT:

                            # Text replace scenario.
                            _, s, e = d[0]
                            self.delete_text(s, e)

                            _, _, new_text = d[1]

                            # Place the new text at the end of the delete for
                            # readability.
                            self.insert_text(e-1, new_text)
                return self.get_text()
        return original
